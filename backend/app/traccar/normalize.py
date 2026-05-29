"""Pure functions that map Traccar's REST JSON onto our fleet domain.

Traccar models devices and positions separately (see its API docs at
https://www.traccar.org/api-reference/): ``GET /api/devices`` returns the fleet
roster, ``GET /api/positions`` returns the latest position per device. These
functions join the two and normalize the quirks of the wire format — notably
that Traccar reports **speed in knots** and carries ignition state inside a
free-form ``attributes`` map.

Everything here is a pure function of its inputs (no I/O, no clock), which keeps
the tricky normalization rules cheap to unit-test against realistic payloads.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.detection.models import GeoPoint, Position
from app.sources.base import FleetVehicle, VehicleSample

# Traccar reports speed over ground in knots; the rest of the app works in m/s.
_KNOTS_TO_MPS = 0.514444


@dataclass(frozen=True, slots=True)
class DeviceReading:
    """A device's identity paired with its freshly normalized position."""

    vehicle: FleetVehicle
    position: Position


def knots_to_mps(knots: float) -> float:
    """Convert a speed in knots (Traccar's unit) to meters per second."""
    return knots * _KNOTS_TO_MPS


def parse_time(raw: object) -> datetime | None:
    """Parse a Traccar ISO-8601 timestamp (``...Z`` suffix included).

    Returns ``None`` for missing or unparseable values so callers can fall back
    to another field rather than crash on a single malformed record.
    """
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _coerce_float(raw: object) -> float:
    """Best-effort float coercion; treats missing/garbage values as 0.0."""
    if isinstance(raw, bool):  # guard: bool is an int subclass in Python
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return 0.0
    return 0.0


def _infer_ignition(attributes: Mapping[str, Any], speed_mps: float) -> bool:
    """Derive ignition state from Traccar attributes, falling back to motion.

    Traccar devices vary in what they report. We prefer the explicit ``ignition``
    attribute, then the ``motion`` attribute, and finally infer from speed so a
    moving vehicle is never reported as "ignition off" purely for lack of data.
    """
    ignition = attributes.get("ignition")
    if isinstance(ignition, bool):
        return ignition
    motion = attributes.get("motion")
    if isinstance(motion, bool):
        return motion
    return speed_mps > 0.0


def to_position(raw: Mapping[str, Any]) -> Position:
    """Normalize a single Traccar position record into a :class:`Position`."""
    attributes = raw.get("attributes")
    if not isinstance(attributes, Mapping):
        attributes = {}
    speed_mps = knots_to_mps(_coerce_float(raw.get("speed")))
    recorded_at = (
        parse_time(raw.get("fixTime"))
        or parse_time(raw.get("deviceTime"))
        or parse_time(raw.get("serverTime"))
    )
    if recorded_at is None:
        raise ValueError("position record has no parseable timestamp")
    return Position(
        point=GeoPoint(
            lat=_coerce_float(raw.get("latitude")),
            lon=_coerce_float(raw.get("longitude")),
        ),
        speed_mps=speed_mps,
        course_deg=_coerce_float(raw.get("course")),
        ignition_on=_infer_ignition(attributes, speed_mps),
        recorded_at=recorded_at,
    )


def to_vehicle(raw: Mapping[str, Any]) -> FleetVehicle:
    """Normalize a Traccar device record into a :class:`FleetVehicle`.

    Traccar identifies devices by a numeric ``id`` and a hardware ``uniqueId``;
    it has no licence-plate concept, so we surface ``uniqueId`` in that slot.
    ``home`` is left ``None`` because a raw feed carries no depot anchor.
    """
    unique_id = str(raw.get("uniqueId") or raw.get("id") or "")
    name = str(raw.get("name") or unique_id or "unknown")
    return FleetVehicle(
        id=str(raw.get("id")),
        name=name,
        plate=unique_id,
        home=None,
    )


def merge_readings(
    devices: Sequence[Mapping[str, Any]],
    positions: Sequence[Mapping[str, Any]],
) -> list[DeviceReading]:
    """Join devices with their latest positions into normalized readings.

    Positions are keyed by ``deviceId``; when a device has several positions the
    most recent (by timestamp) wins. Devices without any position, and positions
    without a recognizable device, are skipped — we only emit vehicles we can
    actually place on the map.
    """
    latest: dict[str, Position] = {}
    for raw_position in positions:
        device_id = raw_position.get("deviceId")
        if device_id is None:
            continue
        try:
            position = to_position(raw_position)
        except ValueError:
            continue
        key = str(device_id)
        existing = latest.get(key)
        if existing is None or position.recorded_at >= existing.recorded_at:
            latest[key] = position

    readings: list[DeviceReading] = []
    for raw_device in devices:
        matched = latest.get(str(raw_device.get("id")))
        if matched is None:
            continue
        readings.append(DeviceReading(vehicle=to_vehicle(raw_device), position=matched))
    return readings


def roster_from_devices(
    devices: Sequence[Mapping[str, Any]],
) -> dict[str, FleetVehicle]:
    """Build a ``device id -> identity`` lookup from Traccar's device roster."""
    return {str(raw.get("id")): to_vehicle(raw) for raw in devices}


def _fallback_vehicle(device_id: str) -> FleetVehicle:
    """Identity for a position whose device is not (yet) in the roster."""
    return FleetVehicle(id=device_id, name=device_id, plate="", home=None)


def apply_positions(
    roster: Mapping[str, FleetVehicle],
    samples: Mapping[str, VehicleSample],
    positions: Sequence[Mapping[str, Any]],
) -> dict[str, VehicleSample]:
    """Merge a batch of streamed positions into the current sample cache.

    Traccar's WebSocket pushes positions incrementally (only for devices that
    just reported), so — unlike the REST snapshot — this updates the cache in
    place: each incoming position becomes the new ``current`` and the prior
    ``current`` is carried forward as ``previous``. Devices not mentioned in the
    batch keep their last sample; positions for an unknown device get a minimal
    fallback identity until the roster catches up. Returns a new dict, leaving
    the input untouched.
    """
    updated = dict(samples)
    for raw in positions:
        device_id = raw.get("deviceId")
        if device_id is None:
            continue
        try:
            position = to_position(raw)
        except ValueError:
            continue
        key = str(device_id)
        previous = updated.get(key)
        updated[key] = VehicleSample(
            vehicle=roster.get(key) or _fallback_vehicle(key),
            current=position,
            previous=previous.current if previous is not None else None,
        )
    return updated
