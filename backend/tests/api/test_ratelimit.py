"""Tests for the per-IP rate limiter and middleware."""

from __future__ import annotations

from app.api.ratelimit import RateLimiter, check_rate_limit
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Pure RateLimiter unit tests (no I/O, no sleep)
# ---------------------------------------------------------------------------


def _make_limiter(limit: int, window: float = 60.0) -> tuple[RateLimiter, list[float]]:
    """Return a limiter with a mutable fake clock."""
    clock: list[float] = [0.0]
    limiter = RateLimiter(limit=limit, window_seconds=window, now=lambda: clock[0])
    return limiter, clock


def test_limiter_allows_requests_under_the_limit() -> None:
    limiter, _ = _make_limiter(limit=3)
    assert limiter.allow("10.0.0.1") is True
    assert limiter.allow("10.0.0.1") is True
    assert limiter.allow("10.0.0.1") is True


def test_limiter_blocks_the_request_over_the_limit() -> None:
    limiter, _ = _make_limiter(limit=3)
    for _ in range(3):
        limiter.allow("10.0.0.1")
    assert limiter.allow("10.0.0.1") is False


def test_limiter_window_resets_after_time_advances() -> None:
    limiter, clock = _make_limiter(limit=2, window=60.0)
    limiter.allow("10.0.0.1")
    limiter.allow("10.0.0.1")
    # Exhausted — should be blocked
    assert limiter.allow("10.0.0.1") is False

    # Advance past the window boundary
    clock[0] = 60.0
    # New window — should be allowed again
    assert limiter.allow("10.0.0.1") is True


def test_limiter_tracks_different_keys_independently() -> None:
    limiter, _ = _make_limiter(limit=1)
    assert limiter.allow("192.168.1.1") is True
    assert limiter.allow("192.168.1.2") is True  # different key, fresh window
    assert limiter.allow("192.168.1.1") is False  # first key exhausted


def test_limiter_disabled_when_limit_is_zero() -> None:
    limiter = RateLimiter(limit=0)
    for _ in range(1000):
        assert limiter.allow("10.0.0.1") is True


def test_retry_after_is_positive() -> None:
    limiter, clock = _make_limiter(limit=1, window=60.0)
    limiter.allow("10.0.0.1")
    # Advance 10 seconds into the window
    clock[0] = 10.0
    retry = limiter.retry_after("10.0.0.1")
    # ~51 seconds remain; retry_after rounds up and adds 1
    assert retry >= 1


def test_retry_after_unknown_key_returns_at_least_one() -> None:
    limiter, _ = _make_limiter(limit=5)
    assert limiter.retry_after("never-seen") >= 1


# ---------------------------------------------------------------------------
# check_rate_limit helper
# ---------------------------------------------------------------------------


def test_check_rate_limit_returns_true_when_within_limit() -> None:
    limiter, _ = _make_limiter(limit=5)
    allowed, retry = check_rate_limit(limiter, "10.0.0.1")
    assert allowed is True
    assert retry == 0


def test_check_rate_limit_returns_false_when_over_limit() -> None:
    limiter, _ = _make_limiter(limit=1)
    limiter.allow("10.0.0.1")  # consume the only slot
    allowed, retry = check_rate_limit(limiter, "10.0.0.1")
    assert allowed is False
    assert retry >= 1


# ---------------------------------------------------------------------------
# App-level integration tests via TestClient
# ---------------------------------------------------------------------------


def _make_settings(rate_limit: int) -> Settings:
    return Settings(
        mock_mode=True,
        cors_origins=("http://localhost:3000",),
        traccar_base_url="http://traccar:8082",
        traccar_ws_url="ws://traccar:8082/api/socket",
        traccar_username="",
        traccar_password="",
        traccar_transport="ws",
        rate_limit_per_minute=rate_limit,
    )


def test_rate_limiting_disabled_never_returns_429() -> None:
    client = TestClient(create_app(_make_settings(rate_limit=0)))
    for _ in range(20):
        response = client.get("/api/vehicles")
        assert response.status_code == 200


def test_rate_limiting_enabled_blocks_after_limit() -> None:
    # Limit of 3: first 3 succeed, 4th is 429
    settings = _make_settings(rate_limit=3)
    client = TestClient(create_app(settings))

    for _ in range(3):
        r = client.get("/api/vehicles")
        assert r.status_code == 200

    r = client.get("/api/vehicles")
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) >= 1
    assert r.json() == {"detail": "rate limit exceeded"}


def test_health_endpoint_is_never_rate_limited() -> None:
    """The /health path must bypass the rate limiter even when enabled."""
    client = TestClient(create_app(_make_settings(rate_limit=1)))
    # Exhaust the /api window first (same IP in TestClient)
    client.get("/api/vehicles")
    client.get("/api/vehicles")

    # /health must still respond 200
    r = client.get("/health")
    assert r.status_code == 200
