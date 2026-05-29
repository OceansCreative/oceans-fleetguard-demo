"""FastAPI application factory for the FleetGuard backend."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.fleet_service import FleetService
from app.api.routes import create_router
from app.api.stream import FleetStreamer
from app.config import Settings


def _build_service(settings: Settings) -> FleetService:
    """Pick the data source: the mock simulation or a live Traccar relay."""
    if settings.mock_mode:
        return FleetService.mock()
    return FleetService.traccar(
        base_url=settings.traccar_base_url,
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
    streamer = FleetStreamer(service)

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
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        """Liveness probe; also reports whether mock mode is active."""
        return {"status": "ok", "mock_mode": resolved.mock_mode}

    app.include_router(create_router(service))

    @app.websocket("/ws/positions")
    async def positions(websocket: WebSocket) -> None:
        """Stream live vehicle positions and alerts to the dashboard."""
        await streamer.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            streamer.disconnect(websocket)

    return app


app = create_app()
