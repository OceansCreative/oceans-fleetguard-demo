"""REST routes for the fleet API."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.alerts.history import AlertHistory
from app.api.fleet_service import FleetService
from app.api.schemas import AlertHistoryEntryOut, AlertOut, VehicleOut

_MAX_HISTORY_LIMIT = 500


def create_router(
    service: FleetService,
    *,
    dependencies: Sequence[Any] | None = None,
    history: AlertHistory | None = None,
) -> APIRouter:
    """Build the ``/api`` router bound to a fleet service instance.

    ``dependencies`` (e.g. an API-key guard) apply to every route on the router.
    ``history`` is the shared alert-history recorder (optional; returns empty list
    when not provided).
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

    @router.get("/alerts/history")
    def get_alert_history(
        limit: int | None = Query(
            default=None,
            ge=1,
            le=_MAX_HISTORY_LIMIT,
            description="Cap the number of returned entries (newest first).",
        ),
    ) -> list[AlertHistoryEntryOut]:
        if history is None:
            return []
        return [
            AlertHistoryEntryOut(
                vehicle_id=e.vehicle_id,
                vehicle_name=e.vehicle_name,
                alert_type=e.alert_type,
                alert_severity=e.alert_severity,
                alert_reason=e.alert_reason,
                lat=e.lat,
                lon=e.lon,
                recorded_at=e.recorded_at,
            )
            for e in history.entries(limit=limit)
        ]

    return router
