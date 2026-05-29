"""Adapts the stateful mock simulation to the :class:`FleetSource` contract."""

from __future__ import annotations

from datetime import datetime

from app.mock.generator import MockFleet
from app.sources.base import VehicleSample


class MockSource:
    """Wraps a :class:`MockFleet` so it can be used wherever a source is expected."""

    def __init__(self, fleet: MockFleet) -> None:
        self._fleet = fleet

    def advance(self, dt_seconds: float, now: datetime) -> None:
        """Step the simulation forward by ``dt_seconds``."""
        self._fleet.step(dt_seconds, now)

    def snapshot(self) -> list[VehicleSample]:
        return self._fleet.samples()

    def close(self) -> None:  # noqa: D401 - nothing to release for the simulation
        """No-op; the simulation holds no external resources."""
