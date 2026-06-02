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


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


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
        api_key: Shared secret required to call ``/api`` and ``/ws/positions``.
            Empty (the default) disables authentication, keeping the keyless
            mock/quickstart open; set it for any exposed deployment.
        notify_webhook_url: URL to POST when a vehicle enters a CRITICAL alert
            state. Empty (the default) disables outbound notifications.
        rate_limit_per_minute: Maximum requests per client IP per minute for
            ``/api`` and ``/ws`` endpoints. ``0`` disables rate limiting
            entirely (default); set a positive value for exposed deployments.
        log_level: Logging level name (case-insensitive), e.g. ``INFO`` or
            ``DEBUG``. Defaults to ``INFO``.
        log_format: ``text`` (default, human-readable) or ``json`` (structured
            JSON lines for log-aggregation pipelines).
        auth_secret: HMAC signing secret for user-login session tokens. Empty
            (the default) disables the login gate entirely — a SECOND, opt-in
            gate independent of ``api_key``. Set it to require a signed session
            token (issued by ``POST /api/auth/login``) on ``/api`` and the WS.
        auth_username: The single login username accepted by the login route.
        auth_password_hash: Lowercase sha256 hex digest of the login password.
            See ``app.api.auth.verify_password`` for the (deliberately simple)
            scheme and its production caveats.
        auth_token_ttl_s: Session-token lifetime in seconds (default 1 hour).
    """

    mock_mode: bool
    cors_origins: tuple[str, ...]
    traccar_base_url: str
    traccar_ws_url: str
    traccar_username: str
    traccar_password: str
    traccar_transport: str
    api_key: str = ""
    notify_webhook_url: str = ""
    rate_limit_per_minute: int = 0
    log_level: str = "INFO"
    log_format: str = "text"
    auth_secret: str = ""
    auth_username: str = ""
    auth_password_hash: str = ""
    auth_token_ttl_s: int = 3600

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
            api_key=os.environ.get("API_KEY", "").strip(),
            notify_webhook_url=os.environ.get("NOTIFY_WEBHOOK_URL", "").strip(),
            rate_limit_per_minute=_get_int("RATE_LIMIT_PER_MINUTE", default=0),
            log_level=os.environ.get("LOG_LEVEL", "INFO").strip().upper(),
            log_format=os.environ.get("LOG_FORMAT", "text").strip().lower(),
            auth_secret=os.environ.get("AUTH_SECRET", "").strip(),
            auth_username=os.environ.get("AUTH_USERNAME", "").strip(),
            auth_password_hash=os.environ.get("AUTH_PASSWORD_HASH", "").strip().lower(),
            auth_token_ttl_s=_get_int("AUTH_TOKEN_TTL_S", default=3600),
        )
