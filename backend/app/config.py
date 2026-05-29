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
    """

    mock_mode: bool
    cors_origins: tuple[str, ...]
    traccar_base_url: str

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the process environment."""
        return cls(
            mock_mode=_get_bool("MOCK_MODE", default=True),
            cors_origins=_get_origins("CORS_ORIGINS", "http://localhost:3000"),
            traccar_base_url=os.environ.get("TRACCAR_BASE_URL", "http://traccar:8082"),
        )
