"""Request-ID middleware for FleetGuard.

For every HTTP request:
  1. Reads ``X-Request-ID`` from the incoming headers, or generates a UUID-4.
  2. Stores the ID in a ``contextvars.ContextVar`` so that log records emitted
     during the request can include it automatically.
  3. Echoes the ID back to the client via ``X-Request-ID`` on the response.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.request_id import (
    generate_request_id,
    set_request_id,
)

_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request-ID to every HTTP request/response cycle."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid = request.headers.get(_HEADER) or generate_request_id()
        set_request_id(rid)
        response = await call_next(request)
        response.headers[_HEADER] = rid
        return response
