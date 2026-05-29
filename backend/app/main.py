"""FastAPI application factory for the FleetGuard backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FleetGuard FastAPI application.

    Args:
        settings: Optional settings override; defaults to environment-derived
            settings. Injecting settings keeps the app easy to test.
    """
    resolved = settings or Settings.from_env()
    app = FastAPI(title="FleetGuard API", version=__version__)

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

    return app


app = create_app()
