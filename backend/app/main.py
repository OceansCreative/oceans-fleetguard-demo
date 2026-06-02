"""FastAPI application factory for the FleetGuard backend."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.auth import make_auth_dependency, token_is_valid
from app.api.fleet_service import FleetService
from app.api.routes import create_auth_router, create_router
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


def _ws_is_authorized(
    settings: Settings, now_fn: Callable[[], int], websocket: WebSocket
) -> bool:
    """Both opt-in gates must pass for the WS handshake.

    Browsers can't set headers on a WebSocket, so the API key arrives as
    ``?key=`` and the session token as ``?token=``. Each check is a no-op when
    its secret is unset, mirroring the REST dependencies.
    """
    params = websocket.query_params
    key_ok = key_is_valid(settings.api_key, params.get("key"))
    token_ok = token_is_valid(settings.auth_secret, now_fn(), params.get("token"))
    return key_ok and token_ok


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
    streamer = FleetStreamer(service, notifier=notifier)

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

    def now_fn() -> int:
        return int(time.time())

    key_guard = make_api_key_dependency(resolved.api_key)
    auth_guard = make_auth_dependency(resolved.auth_secret, now_fn)
    app.include_router(create_auth_router(resolved, now_fn=now_fn))
    app.include_router(
        create_router(service, dependencies=[Depends(key_guard), Depends(auth_guard)])
    )

    @app.websocket("/ws/positions")
    async def positions(websocket: WebSocket) -> None:
        """Stream live vehicle positions and alerts to the dashboard.

        Browsers can't set headers on a WebSocket handshake, so the API key
        (``?key=``) and the session token (``?token=``) are passed as query
        parameters. Both opt-in gates must pass when enabled.
        """
        if not _ws_is_authorized(resolved, now_fn, websocket):
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
