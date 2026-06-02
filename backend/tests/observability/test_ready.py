"""Tests for the /ready endpoint and ReadinessState."""

from __future__ import annotations

from app.config import Settings
from app.main import create_app
from app.observability.ready import ReadinessState
from fastapi.testclient import TestClient


def _settings() -> Settings:
    return Settings(
        mock_mode=True,
        cors_origins=("http://localhost:3000",),
        traccar_base_url="http://traccar:8082",
        traccar_ws_url="ws://traccar:8082/api/socket",
        traccar_username="",
        traccar_password="",
        traccar_transport="ws",
    )


class TestReadinessState:
    def test_not_ready_initially(self) -> None:
        state = ReadinessState()
        assert state.is_ready() is False

    def test_ready_after_mark(self) -> None:
        state = ReadinessState()
        state.mark_ready()
        assert state.is_ready() is True

    def test_mark_ready_is_idempotent(self) -> None:
        state = ReadinessState()
        state.mark_ready()
        state.mark_ready()
        assert state.is_ready() is True


class TestReadyEndpoint:
    def test_returns_503_before_ready(self) -> None:
        # Inject a ReadinessState that has NOT been marked ready so we can
        # test the 503 path without running the full lifespan.
        state = ReadinessState()
        app = create_app(_settings(), readiness=state)
        # Use raise_server_exceptions=False so 503 is returned, not raised.
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "starting"

    def test_returns_200_after_ready(self) -> None:
        state = ReadinessState()
        state.mark_ready()
        app = create_app(_settings(), readiness=state)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_lifespan_marks_ready(self) -> None:
        # The full lifespan (via TestClient context manager) should call
        # service.start() → mark_ready(), so /ready returns 200 inside it.
        state = ReadinessState()
        app = create_app(_settings(), readiness=state)
        with TestClient(app) as client:
            resp = client.get("/ready")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ready"

    def test_ready_is_unauthenticated(self) -> None:
        # /ready must be accessible without an API key even when one is set.
        state = ReadinessState()
        state.mark_ready()
        settings = Settings(
            mock_mode=True,
            cors_origins=("http://localhost:3000",),
            traccar_base_url="http://traccar:8082",
            traccar_ws_url="ws://traccar:8082/api/socket",
            traccar_username="",
            traccar_password="",
            traccar_transport="ws",
            api_key="super-secret",
        )
        app = create_app(settings, readiness=state)
        client = TestClient(app, raise_server_exceptions=False)
        # No key provided — should still return 200 from /ready
        resp = client.get("/ready")
        assert resp.status_code == 200
