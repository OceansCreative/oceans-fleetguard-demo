"""Mock fleet simulation for running the dashboard without a live Traccar feed."""

from __future__ import annotations

from app.mock.generator import DEFAULT_FLEET, MockFleet, MockVehicle
from app.sources.base import VehicleSample

__all__ = ["DEFAULT_FLEET", "MockFleet", "MockVehicle", "VehicleSample"]
