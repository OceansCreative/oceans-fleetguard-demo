"""FastAPI application factory for the FleetGuard backend."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Callable

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.fleet_service import FleetService
from app.api.routes import create_router
from app.api.security import key_is_valid, make_api_key_dependency
from app.api.stream import FleetStreamer
from app.config import Settings
from app.notify.webhook import CriticalAlertNotifier
from app.observability import ReadinessState, configure_logging
from app.observability.middleware import RequestIDMiddleware


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
    api_key: str,
) -> None:
    """Register the WebSocket positions route."""

    @app.websocket("/ws/positions")
    async def positions(websocket: WebSocket) -> None:
        """Stream live vehicle positions and alerts to the dashboard.

        Browsers can't set headers on a WebSocket handshake, so the API key is
        passed as a ``?key=`` query parameter when authentication is enabled.
        """
        if not key_is_valid(api_key, websocket.query_params.get("key")):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        await streamer.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            streamer.disconnect(websocket)


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
    streamer = FleetStreamer(svc, notifier=notifier)
    _readiness = readiness or ReadinessState()

    app = FastAPI(
        title="FleetGuard API",
        version=__version__,
        lifespan=_make_lifespan(svc, streamer, _readiness),
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
    )

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
        if _readiness.is_ready():
            return JSONResponse({"status": "ready"})
        return JSONResponse({"status": "starting"}, status_code=503)

    guard = make_api_key_dependency(resolved.api_key)
    app.include_router(create_router(svc, dependencies=[Depends(guard)]))
    _add_ws_route(app, streamer, resolved.api_key)

    return app


app = create_app()
