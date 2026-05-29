"""Tests for the REST routes via the FastAPI test client."""

from __future__ import annotations

from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def _client(*, mock_mode: bool = True) -> TestClient:
    settings = Settings(
        mock_mode=mock_mode,
        cors_origins=("http://localhost:3000",),
        traccar_base_url="http://traccar:8082",
    )
    # No context manager: REST tests do not need the streaming lifespan.
    return TestClient(create_app(settings))


def test_list_vehicles_returns_the_mock_fleet() -> None:
    response = _client().get("/api/vehicles")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_get_known_vehicle() -> None:
    response = _client().get("/api/vehicles/v-001")
    assert response.status_code == 200
    assert response.json()["id"] == "v-001"


def test_get_unknown_vehicle_is_404() -> None:
    response = _client().get("/api/vehicles/nope")
    assert response.status_code == 404


def test_list_alerts_returns_a_list() -> None:
    response = _client().get("/api/alerts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_mock_disabled_serves_an_empty_fleet() -> None:
    response = _client(mock_mode=False).get("/api/vehicles")
    assert response.status_code == 200
    assert response.json() == []
