"""Context-variable storage for the authenticated principal (username).

Mirrors :mod:`app.observability.request_id`: the auth dependency stamps the
logged-in username here after verifying a session token, so every log record
emitted while serving that request can attribute it to a user (audit trail).

Pure logic — no Starlette/FastAPI imports — so it unit-tests without any ASGI
machinery. The value defaults to ``None`` and each request runs in its own
copied context, so an unauthenticated request never inherits a stale user.
"""

from __future__ import annotations

from contextvars import ContextVar

_principal_var: ContextVar[str | None] = ContextVar("principal", default=None)


def set_principal(username: str) -> None:
    """Store *username* as the authenticated principal for this request."""
    _principal_var.set(username)


def current_principal() -> str | None:
    """Return the principal for the current task, or ``None`` if unauthenticated."""
    return _principal_var.get()
