"""A deterministic mock fleet that wanders around the Matsue / Yasugi / Yonago area.

The simulation is seedable so tests are reproducible. One vehicle is driven into
a deliberate "suspicious" scenario (moving with the ignition off) so the
dashboard demonstrates live theft alerts out of the box.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime

from app.detection.geo import destination_point, haversine_m
from app.detection.models import CircularGeofence, GeoPoint, Position
from app.sources.base import FleetVehicle, VehicleSample

# A mock vehicle is just a fleet vehicle whose geofence is always known, so we
# reuse the source-agnostic identity type directly.
MockVehicle = FleetVehicle

# Anchor points (approximate town centers) the mock fleet patrols around.
MATSUE = GeoPoint(lat=35.4723, lon=133.0505)
YASUGI = GeoPoint(lat=35.4309, lon=133.2503)
YONAGO = GeoPoint(lat=35.4281, lon=133.3311)

# How far a vehicle may stray from its anchor before it steers back (meters).
_LEASH_M = 2_500.0
# Geofence radius for the detection rule (vehicles patrol within the leash, so a
# wider geofence only trips when one is driven away deliberately).
_GEOFENCE_RADIUS_M = 3_000.0
_MAX_TURN_DEG = 25.0
_CRUISE_SPEED_MPS = 12.0


def _mock_vehicle(id: str, name: str, plate: str, anchor: GeoPoint) -> MockVehicle:
    return FleetVehicle(
        id=id,
        name=name,
        plate=plate,
        geofence=CircularGeofence(center=anchor, radius_m=_GEOFENCE_RADIUS_M),
    )


DEFAULT_FLEET: tuple[MockVehicle, ...] = (
    _mock_vehicle("v-001", "Van 01", "matsue 800 a 10-01", MATSUE),
    _mock_vehicle("v-002", "Van 02", "matsue 800 a 10-02", MATSUE),
    _mock_vehicle("v-003", "Truck 01", "yasugi 800 a 20-01", YASUGI),
    _mock_vehicle("v-004", "Truck 02", "yonago 800 a 30-01", YONAGO),
    # Driven into a theft scenario so alerts fire out of the box.
    _mock_vehicle("v-005", "Van 03", "yonago 800 a 30-02", YONAGO),
)

_SUSPICIOUS_ID = "v-005"


@dataclass
class _Runtime:
    vehicle: MockVehicle
    home: GeoPoint
    heading_deg: float
    current: Position
    previous: Position | None


def _bearing_deg(origin: GeoPoint, target: GeoPoint) -> float:
    """Initial great-circle bearing from ``origin`` to ``target`` (deg)."""
    d_lon = math.radians(target.lon - origin.lon)
    lat1, lat2 = math.radians(origin.lat), math.radians(target.lat)
    y = math.sin(d_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(
        d_lon
    )
    return math.degrees(math.atan2(y, x)) % 360.0


class MockFleet:
    """Stateful simulation advanced in fixed steps."""

    def __init__(
        self,
        start_time: datetime,
        vehicles: tuple[MockVehicle, ...] = DEFAULT_FLEET,
        seed: int = 42,
    ) -> None:
        self._rng = random.Random(seed)
        self._runtime = [self._spawn(v, start_time) for v in vehicles]

    def _spawn(self, vehicle: MockVehicle, start_time: datetime) -> _Runtime:
        if vehicle.geofence is None:  # pragma: no cover - mock vehicles set it
            raise ValueError(f"mock vehicle {vehicle.id} is missing a geofence")
        anchor = vehicle.geofence.center
        heading = self._rng.uniform(0.0, 360.0)
        current = Position(
            point=anchor,
            speed_mps=0.0,
            course_deg=heading,
            ignition_on=True,
            recorded_at=start_time,
        )
        return _Runtime(
            vehicle=vehicle,
            home=anchor,
            heading_deg=heading,
            current=current,
            previous=None,
        )

    def step(self, dt_seconds: float, now: datetime) -> None:
        """Advance every vehicle by ``dt_seconds``."""
        for runtime in self._runtime:
            self._advance_one(runtime, dt_seconds, now)

    def samples(self) -> list[VehicleSample]:
        """Snapshot the current and previous position of each vehicle."""
        return [
            VehicleSample(
                vehicle=runtime.vehicle,
                current=runtime.current,
                previous=runtime.previous,
            )
            for runtime in self._runtime
        ]

    def _advance_one(self, runtime: _Runtime, dt_seconds: float, now: datetime) -> None:
        suspicious = runtime.vehicle.id == _SUSPICIOUS_ID
        heading = self._next_heading(runtime, suspicious)
        point = destination_point(
            runtime.current.point, heading, _CRUISE_SPEED_MPS * dt_seconds
        )
        runtime.previous = runtime.current
        runtime.heading_deg = heading
        runtime.current = Position(
            point=point,
            speed_mps=_CRUISE_SPEED_MPS,
            course_deg=heading,
            ignition_on=not suspicious,
            recorded_at=now,
        )

    def _next_heading(self, runtime: _Runtime, suspicious: bool) -> float:
        home = runtime.home
        here = runtime.current.point
        if suspicious:
            # Steadily flee from home to also trip the geofence rule.
            return _bearing_deg(home, here)
        if haversine_m(here, home) > _LEASH_M:
            return _bearing_deg(here, home)
        jitter = self._rng.uniform(-_MAX_TURN_DEG, _MAX_TURN_DEG)
        return (runtime.heading_deg + jitter) % 360.0
