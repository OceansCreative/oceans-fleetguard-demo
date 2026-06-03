"""Tests for API-key authentication on the REST and WebSocket endpoints."""

from __future__ import annotations

import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def _settings(api_key: str = "") -> Settings:
    return Settings(
        mock_mode=True,
        cors_origins=("http://localhost:3000",),
        traccar_base_url="http://traccar:8082",
        traccar_ws_url="ws://traccar:8082/api/socket",
        traccar_username="",
        traccar_password="",
        traccar_transport="ws",
        api_key=api_key,
    )


def _client(api_key: str = "") -> TestClient:
    return TestClient(create_app(_settings(api_key)))


# --- REST -----------------------------------------------------------------


def test_rest_is_open_when_no_key_is_configured() -> None:
    assert _client().get("/api/vehicles").status_code == 200


def test_rest_rejects_a_missing_key_when_one_is_configured() -> None:
    response = _client(api_key="s3cret").get("/api/vehicles")
    assert response.status_code == 401


def test_rest_accepts_the_x_api_key_header() -> None:
    response = _client(api_key="s3cret").get(
        "/api/vehicles", headers={"X-API-Key": "s3cret"}
    )
    assert response.status_code == 200


def test_rest_accepts_a_bearer_token() -> None:
    response = _client(api_key="s3cret").get(
        "/api/vehicles", headers={"Authorization": "Bearer s3cret"}
    )
    assert response.status_code == 200


def test_rest_rejects_a_wrong_key() -> None:
    response = _client(api_key="s3cret").get(
        "/api/vehicles", headers={"X-API-Key": "nope"}
    )
    assert response.status_code == 401


def test_health_stays_open_even_with_a_key_configured() -> None:
    assert _client(api_key="s3cret").get("/health").status_code == 200


# --- WebSocket ------------------------------------------------------------


def test_ws_is_open_when_no_key_is_configured() -> None:
    with (
        _client() as client,
        client.websocket_connect("/ws/positions") as websocket,
    ):
        assert "vehicles" in websocket.receive_json()


def test_ws_accepts_the_key_query_parameter() -> None:
    with (
        _client(api_key="s3cret") as client,
        client.websocket_connect("/ws/positions?key=s3cret") as websocket,
    ):
        assert "vehicles" in websocket.receive_json()


def test_ws_rejects_a_missing_or_wrong_key() -> None:
    with (
        _client(api_key="s3cret") as client,
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/ws/positions") as websocket,
    ):
        websocket.receive_json()
