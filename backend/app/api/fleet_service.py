"""Fleet service: advances the mock fleet and runs detection per vehicle."""

from __future__ import annotations

from datetime import UTC, datetime, time

from app.api.schemas import AlertOut, VehicleOut
from app.detection.engine import detect
from app.detection.models import (
    BusinessHours,
    CircularGeofence,
    DetectionConfig,
)
from app.mock.generator import MockFleet, MockVehicle

_BUSINESS_HOURS = BusinessHours(
    operating_days=frozenset({0, 1, 2, 3, 4}),
    start=time(8, 0),
    end=time(19, 0),
)
_GEOFENCE_RADIUS_M = 3_000.0


def _utcnow() -> datetime:
    return datetime.now(UTC)


class FleetService:
    """Bridges the simulation and the detection engine into API payloads."""

    def __init__(self, fleet: MockFleet) -> None:
        self._fleet = fleet

    @classmethod
    def mock(cls, start_time: datetime | None = None, seed: int = 42) -> FleetService:
        return cls(MockFleet(start_time=start_time or _utcnow(), seed=seed))

    @classmethod
    def empty(cls, start_time: datetime | None = None) -> FleetService:
        return cls(MockFleet(start_time=start_time or _utcnow(), vehicles=()))

    def advance(self, dt_seconds: float, now: datetime | None = None) -> None:
        """Step the simulation forward."""
        self._fleet.step(dt_seconds, now or _utcnow())

    def vehicles(self) -> list[VehicleOut]:
        """Current vehicles, each with freshly evaluated alerts."""
        return [
            VehicleOut.from_sample(
                sample,
                detect(
                    sample.current, self._config_for(sample.vehicle), sample.previous
                ),
            )
            for sample in self._fleet.samples()
        ]

    def vehicle(self, vehicle_id: str) -> VehicleOut | None:
        return next((v for v in self.vehicles() if v.id == vehicle_id), None)

    def alerts(self) -> list[AlertOut]:
        return [alert for vehicle in self.vehicles() for alert in vehicle.alerts]

    @staticmethod
    def _config_for(vehicle: MockVehicle) -> DetectionConfig:
        return DetectionConfig(
            geofence=CircularGeofence(center=vehicle.home, radius_m=_GEOFENCE_RADIUS_M),
            business_hours=_BUSINESS_HOURS,
        )
