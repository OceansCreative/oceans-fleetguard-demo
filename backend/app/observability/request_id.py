"""Context-variable storage for the per-request ID.

Pure logic — no Starlette imports — so the ID generation and retrieval can be
unit-tested without any ASGI machinery.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    """Return a fresh UUID-4 string."""
    return str(uuid.uuid4())


def set_request_id(rid: str) -> None:
    """Store *rid* in the current task's context."""
    _request_id_var.set(rid)


def current_request_id() -> str | None:
    """Return the request-ID for the current task, or *None* outside a request."""
    return _request_id_var.get()
