"""Tests for the health endpoint and the application factory."""

from __future__ import annotations

from app.config import Settings
from app.main import _build_service, create_app
from app.sources.mock_source import MockSource
from app.traccar.source import TraccarSource
from app.traccar.stream_source import TraccarStreamSource
from fastapi.testclient import TestClient


def _settings(*, mock_mode: bool, transport: str = "ws") -> Settings:
    return Settings(
        mock_mode=mock_mode,
        cors_origins=("http://localhost:3000",),
        traccar_base_url="http://traccar:8082",
        traccar_ws_url="ws://traccar:8082/api/socket",
        traccar_username="",
        traccar_password="",
        traccar_transport=transport,
    )


def _client(*, mock_mode: bool) -> TestClient:
    return TestClient(create_app(_settings(mock_mode=mock_mode)))


def test_health_reports_ok_and_mock_mode_enabled() -> None:
    response = _client(mock_mode=True).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mock_mode": True}


def test_health_reflects_mock_mode_disabled() -> None:
    response = _client(mock_mode=False).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mock_mode": False}


def test_build_service_uses_the_mock_fleet_in_mock_mode() -> None:
    service = _build_service(_settings(mock_mode=True))
    assert isinstance(service._source, MockSource)


def test_build_service_polls_rest_when_transport_is_rest() -> None:
    service = _build_service(_settings(mock_mode=False, transport="rest"))
    assert isinstance(service._source, TraccarSource)


def test_build_service_streams_over_the_websocket_by_default() -> None:
    service = _build_service(_settings(mock_mode=False, transport="ws"))
    assert isinstance(service._source, TraccarStreamSource)


def test_build_service_falls_back_to_streaming_for_an_unknown_transport() -> None:
    # Any value other than "rest" (here a plausible typo) streams over the
    # WebSocket rather than silently doing nothing.
    service = _build_service(_settings(mock_mode=False, transport="websocket"))
    assert isinstance(service._source, TraccarStreamSource)
