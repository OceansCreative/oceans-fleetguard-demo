"""Runtime configuration loaded from environment variables.

Kept dependency-free and immutable so it is trivial to construct in tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def _get_origins(name: str, default: str) -> tuple[str, ...]:
    raw = os.environ.get(name, default)
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings.

    Attributes:
        mock_mode: When True, the backend serves simulated vehicles instead of
            relaying a live Traccar instance.
        cors_origins: Allowed CORS origins for the frontend.
        traccar_base_url: Base URL of the upstream Traccar server.
        traccar_ws_url: WebSocket URL of the Traccar live feed (``/api/socket``).
        traccar_username: Traccar account (email) used for authentication.
        traccar_password: Password for ``traccar_username``.
        traccar_transport: How to relay live data — ``"ws"`` streams over the
            WebSocket (default), ``"rest"`` polls the REST API on each tick.
    """

    mock_mode: bool
    cors_origins: tuple[str, ...]
    traccar_base_url: str
    traccar_ws_url: str
    traccar_username: str
    traccar_password: str
    traccar_transport: str

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the process environment."""
        base_url = os.environ.get("TRACCAR_BASE_URL", "http://traccar:8082")
        return cls(
            mock_mode=_get_bool("MOCK_MODE", default=True),
            cors_origins=_get_origins("CORS_ORIGINS", "http://localhost:3000"),
            traccar_base_url=base_url,
            traccar_ws_url=os.environ.get(
                "TRACCAR_WS_URL", "ws://traccar:8082/api/socket"
            ),
            traccar_username=os.environ.get("TRACCAR_USERNAME", ""),
            traccar_password=os.environ.get("TRACCAR_PASSWORD", ""),
            traccar_transport=os.environ.get("TRACCAR_TRANSPORT", "ws").strip().lower(),
        )
