"""Per-client-IP rate limiting for REST and WebSocket endpoints.

Design
------
* ``RateLimiter`` is a pure, clock-injectable fixed-window counter.  It has
  no I/O and is fully testable without sleeping.
* ``RateLimitMiddleware`` wraps a Starlette/FastAPI app and applies the limiter
  to every ``/api`` request, keyed by the remote IP address.  ``/health`` and
  any path that does not start with ``/api`` is skipped.
* ``check_rate_limit`` is a thin helper the WebSocket handler uses so that
  ``/ws/positions`` is also protected without going through HTTP middleware.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

# Buckets older than this many seconds above the window size are pruned to
# keep memory usage O(active-clients) rather than O(all-time-clients).
_PRUNE_AGE_FACTOR = 2


@dataclass
class _Bucket:
    """State for a single fixed-window counter."""

    window_start: float
    count: int = 0


@dataclass
class RateLimiter:
    """Fixed-window rate limiter with an injectable clock.

    Args:
        limit: Maximum number of requests allowed per *window_seconds* window.
            A value of ``0`` disables limiting (``allow`` always returns
            ``True``).
        window_seconds: Duration of each fixed window in seconds (default 60).
        now: Callable returning the current epoch time; defaults to
            :func:`time.monotonic`.  Inject a lambda in tests to avoid real
            sleeping.
    """

    limit: int
    window_seconds: float = 60.0
    now: Callable[[], float] = field(default_factory=lambda: time.monotonic)

    _buckets: dict[str, _Bucket] = field(default_factory=dict, init=False, repr=False)

    def allow(self, key: str) -> bool:
        """Return ``True`` and consume a slot if the key is within its limit.

        Returns ``True`` unconditionally when ``self.limit == 0``.
        """
        if self.limit == 0:
            return True

        current = self.now()
        bucket = self._buckets.get(key)

        if bucket is None or (current - bucket.window_start) >= self.window_seconds:
            self._buckets[key] = _Bucket(window_start=current, count=1)
            self._maybe_prune(current)
            return True

        if bucket.count < self.limit:
            bucket.count += 1
            return True

        return False

    def retry_after(self, key: str) -> int:
        """Seconds until the current window resets for *key* (at least 1)."""
        bucket = self._buckets.get(key)
        if bucket is None:
            return 1
        remaining = self.window_seconds - (self.now() - bucket.window_start)
        return max(1, int(remaining) + 1)

    def _maybe_prune(self, current: float) -> None:
        """Remove stale buckets to keep memory bounded."""
        cutoff = current - self.window_seconds * _PRUNE_AGE_FACTOR
        stale = [k for k, b in self._buckets.items() if b.window_start < cutoff]
        for k in stale:
            del self._buckets[k]


def _client_ip(request: Request) -> str:
    """Return the best-effort remote IP for *request*."""
    if request.client is not None:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that enforces a ``RateLimiter`` on ``/api`` paths.

    Requests to paths that do *not* start with ``/api`` are passed through
    unchanged.  On excess, a ``429 Too Many Requests`` JSON response is
    returned with a ``Retry-After`` header.
    """

    def __init__(self, app: ASGIApp, limiter: RateLimiter) -> None:
        super().__init__(app)
        self._limiter = limiter

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path.startswith("/api"):
            ip = _client_ip(request)
            if not self._limiter.allow(ip):
                retry = self._limiter.retry_after(ip)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded"},
                    headers={"Retry-After": str(retry)},
                )
        return await call_next(request)


def check_rate_limit(limiter: RateLimiter, key: str) -> tuple[bool, int]:
    """Check and consume a slot for *key*.

    Returns ``(allowed, retry_after_seconds)``.  When *allowed* is ``True``
    the slot has already been consumed.  When ``False``, ``retry_after`` is
    the number of seconds until the window resets.
    """
    if limiter.allow(key):
        return True, 0
    return False, limiter.retry_after(key)
