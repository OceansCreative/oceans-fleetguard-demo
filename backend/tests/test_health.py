"""Tests for the health endpoint and the application factory."""

from __future__ import annotations

from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def _client(*, mock_mode: bool) -> TestClient:
    settings = Settings(
        mock_mode=mock_mode,
        cors_origins=("http://localhost:3000",),
        traccar_base_url="http://traccar:8082",
        traccar_username="",
        traccar_password="",
    )
    return TestClient(create_app(settings))


def test_health_reports_ok_and_mock_mode_enabled() -> None:
    response = _client(mock_mode=True).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mock_mode": True}


def test_health_reflects_mock_mode_disabled() -> None:
    response = _client(mock_mode=False).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mock_mode": False}
