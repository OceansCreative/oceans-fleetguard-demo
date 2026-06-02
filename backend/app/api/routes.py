"""REST routes for the fleet API."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.auth import issue_token, verify_password
from app.api.fleet_service import FleetService
from app.api.schemas import AlertOut, LoginRequest, LoginResponse, VehicleOut
from app.config import Settings


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


def create_auth_router(settings: Settings, *, now_fn: Callable[[], int]) -> APIRouter:
    """Build the ``/api/auth`` router (login), which is NOT behind the gate.

    The login route must stay open so users can obtain a token; ``now_fn``
    supplies the issuing time, injected for testability. When ``auth_secret``
    is empty the login gate is disabled and the route always returns 401.
    """
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/login")
    def login(body: LoginRequest) -> LoginResponse:
        valid = (
            bool(settings.auth_secret)
            and body.username == settings.auth_username
            and verify_password(settings.auth_password_hash, body.password)
        )
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        now = now_fn()
        token = issue_token(
            settings.auth_secret, body.username, now, settings.auth_token_ttl_s
        )
        return LoginResponse(token=token, expires_at=now + settings.auth_token_ttl_s)

    return router
