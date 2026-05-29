"""Tests for the REST routes via the FastAPI test client."""

from __future__ import annotations

from app.api.fleet_service import FleetService
from app.config import Settings
from app.main import create_app
from app.traccar.source import TraccarSource
from fastapi.testclient import TestClient

from tests.traccar._helpers import DEVICES, POSITIONS, build_client, static_handler


def _settings(*, mock_mode: bool = True) -> Settings:
    return Settings(
        mock_mode=mock_mode,
        cors_origins=("http://localhost:3000",),
        traccar_base_url="http://traccar:8082",
        traccar_username="",
        traccar_password="",
    )


def _client(*, mock_mode: bool = True) -> TestClient:
    # No context manager: REST tests do not need the streaming lifespan.
    return TestClient(create_app(_settings(mock_mode=mock_mode)))


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


def test_mock_disabled_relays_normalized_traccar_vehicles() -> None:
    # With the mock off, the API relays a live Traccar feed; inject a fake
    # upstream so the test stays offline and deterministic.
    source = TraccarSource(build_client(static_handler(DEVICES, POSITIONS)))
    app = create_app(_settings(mock_mode=False), service=FleetService(source))
    response = TestClient(app).get("/api/vehicles")
    assert response.status_code == 200
    body = response.json()
    assert {v["id"] for v in body} == {"1", "2"}  # ghost device dropped
    assert {v["plate"] for v in body} == {"matsue-001", "yasugi-002"}
