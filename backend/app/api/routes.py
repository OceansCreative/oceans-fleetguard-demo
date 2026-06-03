"""REST routes for the fleet API."""

from __future__ import annotations

import hmac
from collections.abc import Callable, Sequence
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.alerts.history import AlertHistory
from app.api.auth import SESSION_COOKIE_NAME, issue_token, verify_password
from app.api.fleet_service import FleetService
from app.api.schemas import (
    AlertHistoryEntryOut,
    AlertOut,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    VehicleOut,
)
from app.config import Settings

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


def create_auth_router(settings: Settings, *, now_fn: Callable[[], int]) -> APIRouter:
    """Build the ``/api/auth`` router (login), which is NOT behind the gate.

    The login route must stay open so users can obtain a token; ``now_fn``
    supplies the issuing time, injected for testability. When ``auth_secret``
    is empty the login gate is disabled and the route always returns 401.
    """
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/login")
    def login(body: LoginRequest, response: Response) -> LoginResponse:
        # Evaluate both factors unconditionally (no short-circuit) and compare
        # the username in constant time, so response latency can't reveal
        # whether a guessed username is valid (user-enumeration side channel).
        user_ok = hmac.compare_digest(
            body.username.encode("utf-8"), settings.auth_username.encode("utf-8")
        )
        pw_ok = verify_password(settings.auth_password_hash, body.password)
        valid = bool(settings.auth_secret) and user_ok and pw_ok
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
        # Also set the token as an httpOnly cookie (XSS-resistant). SameSite=Lax
        # works for a same-origin deployment behind a reverse proxy; cross-origin
        # callers can keep using the Bearer token from the response body.
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            max_age=settings.auth_token_ttl_s,
            httponly=True,
            secure=settings.auth_cookie_secure,
            samesite="lax",
            path="/",
        )
        return LoginResponse(token=token, expires_at=now + settings.auth_token_ttl_s)

    @router.post("/logout")
    def logout(response: Response) -> LogoutResponse:
        """Clear the session cookie. Safe to call when not logged in."""
        response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
        return LogoutResponse(ok=True)

    return router
