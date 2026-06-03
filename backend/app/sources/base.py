"""The common contract shared by every fleet data source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.detection.models import CircularGeofence, Position


@dataclass(frozen=True, slots=True)
class FleetVehicle:
    """Static identity of a vehicle, independent of its data source.

    Attributes:
        id: Stable unique identifier.
        name: Human-readable name.
        plate: Licence plate (mock data only in this repo).
        geofence: The vehicle's allowed area for the geofence rule. ``None`` when
            the source supplies no geofence (e.g. a Traccar device with none
            assigned), which disables that rule while the others stay active.
    """

    id: str
    name: str
    plate: str
    geofence: CircularGeofence | None


@dataclass(frozen=True, slots=True)
class VehicleSample:
    """A vehicle's current position and the previous one (if known)."""

    vehicle: FleetVehicle
    current: Position
    previous: Position | None


@runtime_checkable
class FleetSource(Protocol):
    """Produces the current fleet state on demand.

    Implementations may be pull-based (the mock advances a simulation, the REST
    relay polls on a tick) or push-based (a WebSocket relay streams updates in
    the background). Callers only depend on this interface:

    - :meth:`start` / :meth:`aclose` bracket the source's lifetime, letting
      push sources spin up and tear down a background consumer task.
    - :meth:`advance` lets pull sources produce their next state on a fixed
      cadence; push sources keep themselves fresh and treat it as a no-op.
    - :meth:`snapshot` reads the current state without any I/O.
    """

    async def start(self) -> None:
        """Begin streaming and/or prime the first snapshot. No-op for the mock."""
        ...

    def advance(self, dt_seconds: float, now: datetime) -> None:
        """Produce the next state: step the simulation or poll upstream.

        ``dt_seconds`` and ``now`` are only meaningful to time-based simulations;
        push-based relays keep themselves fresh and ignore this call.
        """
        ...

    def snapshot(self) -> list[VehicleSample]:
        """Return the latest sample for every vehicle in the fleet."""
        ...

    async def aclose(self) -> None:
        """Stop any background work and release resources. No-op for the mock."""
        ...
