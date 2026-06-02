"""FastAPI application factory for the FleetGuard backend."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.alerts.history import AlertHistory
from app.api.fleet_service import FleetService
from app.api.routes import create_router
from app.api.security import key_is_valid, make_api_key_dependency
from app.api.stream import FleetStreamer
from app.config import Settings
from app.notify.webhook import CriticalAlertNotifier


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


def create_app(
    settings: Settings | None = None, *, service: FleetService | None = None
) -> FastAPI:
    """Create and configure the FleetGuard FastAPI application.

    Args:
        settings: Optional settings override; defaults to environment-derived
            settings. Injecting settings keeps the app easy to test.
        service: Optional pre-built fleet service. Injecting one lets tests
            exercise the live-relay wiring with a fake upstream instead of a
            real Traccar server.
    """
    resolved = settings or Settings.from_env()
    service = service or _build_service(resolved)
    notifier = CriticalAlertNotifier(resolved.notify_webhook_url)
    alert_history = AlertHistory()
    streamer = FleetStreamer(service, notifier=notifier, history=alert_history)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await service.start()
        streamer.start()
        try:
            yield
        finally:
            await streamer.stop()
            await service.aclose()

    app = FastAPI(title="FleetGuard API", version=__version__, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        """Liveness probe; also reports whether mock mode is active.

        Unauthenticated by design, so orchestrators can probe it.
        """
        return {"status": "ok", "mock_mode": resolved.mock_mode}

    guard = make_api_key_dependency(resolved.api_key)
    app.include_router(
        create_router(service, dependencies=[Depends(guard)], history=alert_history)
    )

    @app.websocket("/ws/positions")
    async def positions(websocket: WebSocket) -> None:
        """Stream live vehicle positions and alerts to the dashboard.

        Browsers can't set headers on a WebSocket handshake, so the API key is
        passed as a ``?key=`` query parameter when authentication is enabled.
        """
        if not key_is_valid(resolved.api_key, websocket.query_params.get("key")):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        await streamer.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            streamer.disconnect(websocket)

    return app


app = create_app()
