"""Source-agnostic fleet abstraction.

A :class:`FleetSource` produces vehicle samples; both the mock simulation and
the live Traccar relay implement it, so the rest of the app is unaware of where
positions come from.
"""

from __future__ import annotations

from app.sources.base import FleetSource, FleetVehicle

__all__ = ["FleetSource", "FleetVehicle"]
