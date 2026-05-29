"""The common contract shared by every fleet data source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.detection.models import GeoPoint, Position


@dataclass(frozen=True, slots=True)
class FleetVehicle:
    """Static identity of a vehicle, independent of its data source.

    Attributes:
        id: Stable unique identifier.
        name: Human-readable name.
        plate: Licence plate (mock data only in this repo).
        home: Geofence reference point. ``None`` when the source cannot supply a
            known depot/anchor (e.g. a raw Traccar feed), which disables the
            geofence rule while leaving the other rules active.
    """

    id: str
    name: str
    plate: str
    home: GeoPoint | None


@dataclass(frozen=True, slots=True)
class VehicleSample:
    """A vehicle's current position and the previous one (if known)."""

    vehicle: FleetVehicle
    current: Position
    previous: Position | None


@runtime_checkable
class FleetSource(Protocol):
    """Produces the current fleet state on demand.

    Implementations may be stateful (the mock advances a simulation) or thin
    relays (Traccar polls live data); callers only depend on this interface.
    The split between :meth:`advance` (produce the next state) and
    :meth:`snapshot` (read the current state) lets the streamer drive updates on
    a fixed cadence without re-fetching on every REST read.
    """

    def advance(self, dt_seconds: float, now: datetime) -> None:
        """Produce the next state: step the simulation or poll upstream.

        ``dt_seconds`` and ``now`` are only meaningful to time-based simulations;
        live relays ignore them and simply re-fetch.
        """
        ...

    def snapshot(self) -> list[VehicleSample]:
        """Return the latest sample for every vehicle in the fleet."""
        ...

    def close(self) -> None:
        """Release any resources (e.g. HTTP connections). No-op for the mock."""
        ...
