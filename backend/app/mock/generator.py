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
from app.detection.models import GeoPoint, Position

# Anchor points (approximate town centers) the mock fleet patrols around.
MATSUE = GeoPoint(lat=35.4723, lon=133.0505)
YASUGI = GeoPoint(lat=35.4309, lon=133.2503)
YONAGO = GeoPoint(lat=35.4281, lon=133.3311)

# How far a vehicle may stray from home before it steers back (meters).
_LEASH_M = 2_500.0
_MAX_TURN_DEG = 25.0
_CRUISE_SPEED_MPS = 12.0


@dataclass(frozen=True, slots=True)
class MockVehicle:
    """Static identity of a simulated vehicle (mock data only)."""

    id: str
    name: str
    plate: str
    home: GeoPoint


@dataclass(frozen=True, slots=True)
class VehicleSample:
    """A simulated vehicle's current and previous position samples."""

    vehicle: MockVehicle
    current: Position
    previous: Position | None


DEFAULT_FLEET: tuple[MockVehicle, ...] = (
    MockVehicle("v-001", "Van 01", "matsue 800 a 10-01", MATSUE),
    MockVehicle("v-002", "Van 02", "matsue 800 a 10-02", MATSUE),
    MockVehicle("v-003", "Truck 01", "yasugi 800 a 20-01", YASUGI),
    MockVehicle("v-004", "Truck 02", "yonago 800 a 30-01", YONAGO),
    # Driven into a theft scenario so alerts fire out of the box.
    MockVehicle("v-005", "Van 03", "yonago 800 a 30-02", YONAGO),
)

_SUSPICIOUS_ID = "v-005"


@dataclass
class _Runtime:
    vehicle: MockVehicle
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
        heading = self._rng.uniform(0.0, 360.0)
        current = Position(
            point=vehicle.home,
            speed_mps=0.0,
            course_deg=heading,
            ignition_on=True,
            recorded_at=start_time,
        )
        return _Runtime(
            vehicle=vehicle, heading_deg=heading, current=current, previous=None
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
        home = runtime.vehicle.home
        here = runtime.current.point
        if suspicious:
            # Steadily flee from home to also trip the geofence rule.
            return _bearing_deg(home, here)
        if haversine_m(here, home) > _LEASH_M:
            return _bearing_deg(here, home)
        jitter = self._rng.uniform(-_MAX_TURN_DEG, _MAX_TURN_DEG)
        return (runtime.heading_deg + jitter) % 360.0
