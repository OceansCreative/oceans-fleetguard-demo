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

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.detection.models import CircularGeofence, GeoPoint, Position
from app.sources.base import FleetVehicle, VehicleSample

# Traccar reports speed over ground in knots; the rest of the app works in m/s.
_KNOTS_TO_MPS = 0.514444

# Traccar stores a circular geofence as WKT: ``CIRCLE (lat lon, radius_m)``.
# Note Traccar's axis order is latitude-then-longitude (not standard WKT).
_CIRCLE_RE = re.compile(
    r"CIRCLE\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)",
    re.IGNORECASE,
)


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
    to another field rather than crash on a single malformed record. A
    zone-less timestamp is pinned to UTC, because mixing naive and aware
    datetimes for the same device makes them uncomparable and would crash the
    "keep the most recent position" merge with a ``TypeError``.
    """
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)  # Python 3.11+ accepts the Z suffix
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _coerce_float(raw: object) -> float:
    """Best-effort float coercion; treats missing/garbage values as 0.0.

    Used for non-positional fields (speed, course) where a degraded 0.0 is a
    sensible default. Coordinates use :func:`_coerce_coordinate` instead.
    """
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


def _coerce_coordinate(raw: object) -> float | None:
    """Coerce a latitude/longitude, returning ``None`` for missing or garbage.

    Unlike :func:`_coerce_float`, a bad coordinate must not silently become 0.0:
    that would strand the vehicle at "Null Island" (0, 0) and feed a fake point
    into geofence/detection logic. Returning ``None`` lets the caller drop the
    position instead. A legitimate ``0.0`` (equator/prime meridian) is kept.
    """
    if isinstance(raw, bool):  # guard: bool is an int subclass in Python
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None


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
    """Normalize a single Traccar position record into a :class:`Position`.

    Raises ``ValueError`` for records that cannot be placed on the map — no
    usable coordinates or no parseable timestamp — so callers drop them rather
    than emit a fabricated point. Callers already skip ``ValueError`` records.
    """
    attributes = raw.get("attributes")
    if not isinstance(attributes, Mapping):
        attributes = {}
    speed_mps = knots_to_mps(_coerce_float(raw.get("speed")))
    lat = _coerce_coordinate(raw.get("latitude"))
    lon = _coerce_coordinate(raw.get("longitude"))
    if lat is None or lon is None:
        raise ValueError("position record has no usable coordinates")
    recorded_at = (
        parse_time(raw.get("fixTime"))
        or parse_time(raw.get("deviceTime"))
        or parse_time(raw.get("serverTime"))
    )
    if recorded_at is None:
        raise ValueError("position record has no parseable timestamp")
    return Position(
        point=GeoPoint(lat=lat, lon=lon),
        speed_mps=speed_mps,
        course_deg=_coerce_float(raw.get("course")),
        ignition_on=_infer_ignition(attributes, speed_mps),
        recorded_at=recorded_at,
    )


def parse_circular_geofence(area: object) -> CircularGeofence | None:
    """Parse a Traccar geofence ``area`` (WKT) into a :class:`CircularGeofence`.

    Only circular geofences are supported; polygons and polylines (and anything
    unparseable) return ``None`` so the geofence rule simply stays off for them.
    """
    if not isinstance(area, str):
        return None
    match = _CIRCLE_RE.search(area)
    if match is None:
        return None
    lat, lon, radius = (float(match.group(i)) for i in (1, 2, 3))
    return CircularGeofence(center=GeoPoint(lat=lat, lon=lon), radius_m=radius)


def geofences_by_id(
    geofences: Sequence[Mapping[str, Any]],
) -> dict[str, CircularGeofence]:
    """Build a ``geofence id -> circle`` lookup, dropping non-circular ones."""
    result: dict[str, CircularGeofence] = {}
    for raw in geofences:
        circle = parse_circular_geofence(raw.get("area"))
        if circle is not None:
            result[str(raw.get("id"))] = circle
    return result


def _pick_geofence(
    raw_device: Mapping[str, Any],
    geofences: Mapping[str, CircularGeofence],
) -> CircularGeofence | None:
    """Return the first circular geofence assigned to a device, if any."""
    ids = raw_device.get("geofenceIds")
    if not isinstance(ids, list):
        return None
    for geofence_id in ids:
        circle = geofences.get(str(geofence_id))
        if circle is not None:
            return circle
    return None


def to_vehicle(
    raw: Mapping[str, Any],
    geofences: Mapping[str, CircularGeofence] | None = None,
) -> FleetVehicle:
    """Normalize a Traccar device record into a :class:`FleetVehicle`.

    Traccar identifies devices by a numeric ``id`` and a hardware ``uniqueId``;
    it has no licence-plate concept, so we surface ``uniqueId`` in that slot.
    When ``geofences`` is supplied, the device's first assigned circular geofence
    (via its ``geofenceIds``) is attached so the geofence rule can run.
    """
    unique_id = str(raw.get("uniqueId") or raw.get("id") or "")
    name = str(raw.get("name") or unique_id or "unknown")
    geofence = _pick_geofence(raw, geofences) if geofences else None
    return FleetVehicle(
        id=str(raw.get("id")),
        name=name,
        plate=unique_id,
        geofence=geofence,
    )


def merge_readings(
    devices: Sequence[Mapping[str, Any]],
    positions: Sequence[Mapping[str, Any]],
    geofences: Mapping[str, CircularGeofence] | None = None,
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
        device_id = raw_device.get("id")
        if device_id is None:
            continue  # an id-less device can't be keyed or matched; skip it
        matched = latest.get(str(device_id))
        if matched is None:
            continue
        vehicle = to_vehicle(raw_device, geofences)
        readings.append(DeviceReading(vehicle=vehicle, position=matched))
    return readings


def roster_from_devices(
    devices: Sequence[Mapping[str, Any]],
    geofences: Mapping[str, CircularGeofence] | None = None,
) -> dict[str, FleetVehicle]:
    """Build a ``device id -> identity`` lookup from Traccar's device roster.

    Devices without an ``id`` are skipped rather than collapsed onto a shared
    ``"None"`` key (which would alias distinct devices together).
    """
    roster: dict[str, FleetVehicle] = {}
    for raw in devices:
        device_id = raw.get("id")
        if device_id is None:
            continue
        roster[str(device_id)] = to_vehicle(raw, geofences)
    return roster


def _fallback_vehicle(device_id: str) -> FleetVehicle:
    """Identity for a position whose device is not (yet) in the roster."""
    return FleetVehicle(id=device_id, name=device_id, plate="", geofence=None)


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
