"""Fleet service: pulls samples from a source and runs detection per vehicle."""

from __future__ import annotations

from datetime import UTC, datetime, time

from app.api.schemas import AlertOut, VehicleOut
from app.detection.engine import detect
from app.detection.models import (
    BusinessHours,
    CircularGeofence,
    DetectionConfig,
)
from app.mock.generator import MockFleet
from app.sources.base import FleetSource, FleetVehicle
from app.sources.mock_source import MockSource
from app.traccar.client import TraccarClient
from app.traccar.source import TraccarSource

_BUSINESS_HOURS = BusinessHours(
    operating_days=frozenset({0, 1, 2, 3, 4}),
    start=time(8, 0),
    end=time(19, 0),
)
_GEOFENCE_RADIUS_M = 3_000.0


def _utcnow() -> datetime:
    return datetime.now(UTC)


class FleetService:
    """Bridges a fleet source and the detection engine into API payloads."""

    def __init__(self, source: FleetSource) -> None:
        self._source = source

    @classmethod
    def mock(cls, start_time: datetime | None = None, seed: int = 42) -> FleetService:
        return cls(MockSource(MockFleet(start_time=start_time or _utcnow(), seed=seed)))

    @classmethod
    def empty(cls, start_time: datetime | None = None) -> FleetService:
        fleet = MockFleet(start_time=start_time or _utcnow(), vehicles=())
        return cls(MockSource(fleet))

    @classmethod
    def traccar(cls, base_url: str, username: str, password: str) -> FleetService:
        """Relay a live Traccar server."""
        client = TraccarClient(base_url=base_url, username=username, password=password)
        return cls(TraccarSource(client))

    async def start(self) -> None:
        """Start the underlying source (e.g. begin a live stream)."""
        await self._source.start()

    def advance(self, dt_seconds: float, now: datetime | None = None) -> None:
        """Advance the source: step the simulation or poll the upstream feed."""
        self._source.advance(dt_seconds, now or _utcnow())

    def vehicles(self) -> list[VehicleOut]:
        """Current vehicles, each with freshly evaluated alerts."""
        return [
            VehicleOut.from_sample(
                sample,
                detect(
                    sample.current, self._config_for(sample.vehicle), sample.previous
                ),
            )
            for sample in self._source.snapshot()
        ]

    def vehicle(self, vehicle_id: str) -> VehicleOut | None:
        return next((v for v in self.vehicles() if v.id == vehicle_id), None)

    def alerts(self) -> list[AlertOut]:
        return [alert for vehicle in self.vehicles() for alert in vehicle.alerts]

    async def aclose(self) -> None:
        """Stop the underlying source and release any resources it holds."""
        await self._source.aclose()

    @staticmethod
    def _config_for(vehicle: FleetVehicle) -> DetectionConfig:
        # The geofence rule only applies when the source knows the vehicle's
        # anchor (the mock does; a raw Traccar feed does not).
        geofence = (
            CircularGeofence(center=vehicle.home, radius_m=_GEOFENCE_RADIUS_M)
            if vehicle.home is not None
            else None
        )
        return DetectionConfig(geofence=geofence, business_hours=_BUSINESS_HOURS)
