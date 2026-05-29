"""Mock fleet simulation for running the dashboard without a live Traccar feed."""

from __future__ import annotations

from app.mock.generator import (
    DEFAULT_FLEET,
    MockFleet,
    MockVehicle,
    VehicleSample,
)

__all__ = ["DEFAULT_FLEET", "MockFleet", "MockVehicle", "VehicleSample"]
