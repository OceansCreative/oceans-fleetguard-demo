"""FastAPI application factory for the FleetGuard backend."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.alerts.history import AlertHistory
from app.api.auth import SESSION_COOKIE_NAME, make_auth_dependency, token_is_valid
from app.api.fleet_service import FleetService
from app.api.ratelimit import RateLimiter, RateLimitMiddleware, check_rate_limit
from app.api.routes import create_auth_router, create_router
from app.api.security import key_is_valid, make_api_key_dependency
from app.api.stream import FleetStreamer
from app.config import Settings
from app.notify.webhook import CriticalAlertNotifier
from app.observability import ReadinessState, configure_logging
from app.observability.middleware import RequestIDMiddleware

# WebSocket close code 1013 = "Try Again Later" (RFC 6455 / IANA)
_WS_TRY_AGAIN_LATER = 1013


async def _reject_ws_rate_limit(websocket: WebSocket, retry_after: int) -> None:
    """Close a WebSocket handshake because the rate limit was exceeded."""
    await websocket.close(
        code=_WS_TRY_AGAIN_LATER,
        reason=f"rate limit exceeded; retry after {retry_after}s",
    )


def _build_limiter(rate_limit_per_minute: int) -> RateLimiter | None:
    """Return a ``RateLimiter`` when rate limiting is enabled, else ``None``."""
    if rate_limit_per_minute > 0:
        return RateLimiter(limit=rate_limit_per_minute)
    return None


def _add_middleware(
    app: FastAPI,
    resolved: Settings,
    limiter: RateLimiter | None,
) -> None:
    """Attach request-ID, CORS and optional rate-limit middleware to *app*."""
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
    )
    if limiter is not None:
        app.add_middleware(RateLimitMiddleware, limiter=limiter)


def _ws_is_authorized(
    settings: Settings, now_fn: Callable[[], int], websocket: WebSocket
) -> bool:
    """Both opt-in gates must pass for the WS handshake.

    Browsers can't set headers on a WebSocket, so the API key arrives as
    ``?key=`` and the session token as ``?token=``. The session token is also
    accepted from the httpOnly cookie the browser sends automatically on a
    same-origin handshake. Each check is a no-op when its secret is unset,
    mirroring the REST dependencies.
    """
    params = websocket.query_params
    key_ok = key_is_valid(settings.api_key, params.get("key"))
    token = params.get("token") or websocket.cookies.get(SESSION_COOKIE_NAME)
    token_ok = token_is_valid(settings.auth_secret, now_fn(), token)
    return key_ok and token_ok


async def _check_ws_access(
    websocket: WebSocket,
    settings: Settings,
    now_fn: Callable[[], int],
    limiter: RateLimiter | None,
) -> bool:
    """Validate auth (API key + session token) and rate limit for a WS connection.

    Returns ``True`` when the connection is permitted; returns ``False`` after
    sending the appropriate close frame so the caller can bail out early. Checks
    run in order: API key, session token (both close 1008), then rate limit
    (closes 1013), all before the streamer accepts the socket.
    """
    if not _ws_is_authorized(settings, now_fn, websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False
    if limiter is not None:
        host = websocket.client.host if websocket.client else "unknown"
        allowed, retry_after = check_rate_limit(limiter, host)
        if not allowed:
            await _reject_ws_rate_limit(websocket, retry_after)
            return False
    return True


def _build_service(settings: Settings) -> FleetService:
    """Pick the data source: the mock simulation or a live Traccar relay.

    A live relay streams over the WebSocket by default; set
    ``TRACCAR_TRANSPORT=rest`` to fall back to REST polling.
    """
    if settings.mock_mode:
        return FleetService.mock()
    if settings.traccar_transport == "rest":
        return FleetService.traccar(
            base_url=settings.traccar_base_url,
            username=settings.traccar_username,
            password=settings.traccar_password,
        )
    return FleetService.traccar_stream(
        base_url=settings.traccar_base_url,
        ws_url=settings.traccar_ws_url,
        username=settings.traccar_username,
        password=settings.traccar_password,
    )


def _make_lifespan(
    service: FleetService,
    streamer: FleetStreamer,
    readiness: ReadinessState,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Return an async-context-manager callable that manages the app's lifespan."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await service.start()
        readiness.mark_ready()
        streamer.start()
        try:
            yield
        finally:
            await streamer.stop()
            await service.aclose()

    return lifespan


def _add_ws_route(
    app: FastAPI,
    streamer: FleetStreamer,
    settings: Settings,
    now_fn: Callable[[], int],
    limiter: RateLimiter | None,
) -> None:
    """Register the WebSocket positions route."""

    @app.websocket("/ws/positions")
    async def positions(websocket: WebSocket) -> None:
        """Stream live vehicle positions and alerts to the dashboard.

        Browsers can't set headers on a WebSocket handshake, so the API key
        (``?key=``) and the session token (``?token=``) are passed as query
        parameters. Both opt-in gates and the rate limit must pass when enabled.
        """
        if not await _check_ws_access(websocket, settings, now_fn, limiter):
            return
        await streamer.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            streamer.disconnect(websocket)


def _add_probes(app: FastAPI, resolved: Settings, readiness: ReadinessState) -> None:
    """Register the open ``/health`` and ``/ready`` probes."""

    @app.get("/health")
    def health() -> dict[str, object]:
        """Liveness probe; also reports whether mock mode is active.

        Unauthenticated by design, so orchestrators can probe it.
        """
        return {"status": "ok", "mock_mode": resolved.mock_mode}

    @app.get("/ready")
    def ready() -> JSONResponse:
        """Readiness probe — returns 200 once the service has started.

        Returns 503 while the fleet service is still initialising so that
        orchestrators (Kubernetes, Compose health-checks) can wait before
        routing live traffic.  Unauthenticated by design, same as ``/health``.
        """
        if readiness.is_ready():
            return JSONResponse({"status": "ready"})
        return JSONResponse({"status": "starting"}, status_code=503)


def _register_routes(
    app: FastAPI,
    resolved: Settings,
    svc: FleetService,
    alert_history: AlertHistory,
    now_fn: Callable[[], int],
) -> None:
    """Wire the auth-login router and the gated REST router (both auth gates)."""
    key_guard = make_api_key_dependency(resolved.api_key)
    auth_guard = make_auth_dependency(resolved.auth_secret, now_fn)
    app.include_router(create_auth_router(resolved, now_fn=now_fn))
    app.include_router(
        create_router(
            svc,
            dependencies=[Depends(key_guard), Depends(auth_guard)],
            history=alert_history,
        )
    )


def create_app(
    settings: Settings | None = None,
    *,
    service: FleetService | None = None,
    readiness: ReadinessState | None = None,
) -> FastAPI:
    """Create and configure the FleetGuard FastAPI application.

    Args:
        settings: Optional settings override; defaults to environment-derived
            settings. Injecting settings keeps the app easy to test.
        service: Optional pre-built fleet service. Injecting one lets tests
            exercise the live-relay wiring with a fake upstream instead of a
            real Traccar server.
        readiness: Optional pre-built readiness state. Injecting one lets tests
            assert 503/200 behaviour without running the full lifespan.
    """
    resolved = settings or Settings.from_env()
    configure_logging(resolved.log_level, json=resolved.log_format == "json")

    svc = service or _build_service(resolved)
    notifier = CriticalAlertNotifier(resolved.notify_webhook_url)
    alert_history = AlertHistory()
    streamer = FleetStreamer(svc, notifier=notifier, history=alert_history)
    limiter = _build_limiter(resolved.rate_limit_per_minute)
    _readiness = readiness or ReadinessState()

    def now_fn() -> int:
        return int(time.time())

    app = FastAPI(
        title="FleetGuard API",
        version=__version__,
        lifespan=_make_lifespan(svc, streamer, _readiness),
    )
    _add_middleware(app, resolved, limiter)
    _add_probes(app, resolved, _readiness)
    _register_routes(app, resolved, svc, alert_history, now_fn)
    _add_ws_route(app, streamer, resolved, now_fn, limiter)

    return app


app = create_app()
