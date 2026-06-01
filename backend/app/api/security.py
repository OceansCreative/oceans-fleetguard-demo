"""API-key authentication for the REST and WebSocket endpoints.

Authentication is opt-in: when no key is configured the guards are no-ops, so
the keyless mock/quickstart keeps working. Set ``API_KEY`` to require a shared
secret on ``/api`` (via the ``X-API-Key`` header or ``Authorization: Bearer``)
and on ``/ws/positions`` (via a ``?key=`` query parameter, since browsers can't
set custom headers on a WebSocket handshake).
"""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from fastapi import Header, HTTPException, status


def _matches(expected: str, provided: str | None) -> bool:
    """Constant-time comparison that is safe against a missing value."""
    if provided is None:
        return False
    return secrets.compare_digest(provided, expected)


def key_is_valid(expected: str, provided: str | None) -> bool:
    """True when auth is disabled (no key configured) or the key matches."""
    if not expected:
        return True
    return _matches(expected, provided)


def make_api_key_dependency(expected: str) -> Callable[..., Awaitable[None]]:
    """Build a FastAPI dependency that enforces the API key on a request.

    When ``expected`` is empty the dependency is a no-op.
    """

    async def dependency(
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        authorization: str | None = Header(default=None),
    ) -> None:
        if not expected:
            return
        provided = x_api_key
        if provided is None and authorization is not None:
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() == "bearer" and token:
                provided = token
        if not _matches(expected, provided):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return dependency
