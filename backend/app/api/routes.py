"""REST routes for the fleet API."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.fleet_service import FleetService
from app.api.schemas import AlertOut, VehicleOut


def create_router(
    service: FleetService, *, dependencies: Sequence[Any] | None = None
) -> APIRouter:
    """Build the ``/api`` router bound to a fleet service instance.

    ``dependencies`` (e.g. an API-key guard) apply to every route on the router.
    """
    router = APIRouter(
        prefix="/api", tags=["fleet"], dependencies=list(dependencies or [])
    )

    @router.get("/vehicles")
    def list_vehicles() -> list[VehicleOut]:
        return service.vehicles()

    @router.get("/vehicles/{vehicle_id}")
    def get_vehicle(vehicle_id: str) -> VehicleOut:
        vehicle = service.vehicle(vehicle_id)
        if vehicle is None:
            raise HTTPException(status_code=404, detail="vehicle not found")
        return vehicle

    @router.get("/alerts")
    def list_alerts() -> list[AlertOut]:
        return service.alerts()

    return router
