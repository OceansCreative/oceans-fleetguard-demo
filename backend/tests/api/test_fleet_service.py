"""Tests for the fleet service that wires the mock fleet to detection."""

from __future__ import annotations

from datetime import UTC, datetime

from app.api.fleet_service import FleetService

START = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)  # Wed noon (business hrs)


def test_vehicles_returns_one_payload_per_mock_vehicle() -> None:
    service = FleetService.mock(start_time=START)
    vehicles = service.vehicles()
    assert len(vehicles) == 5
    assert {"v-001", "v-005"} <= {v.id for v in vehicles}


def test_suspicious_vehicle_alerts_after_moving() -> None:
    service = FleetService.mock(start_time=START)
    service.advance(2.0, START)  # ignition off + now moving
    suspicious = service.vehicle("v-005")
    assert suspicious is not None
    assert "ignition_off_movement" in {alert.type for alert in suspicious.alerts}


def test_stationary_fleet_has_no_alerts() -> None:
    service = FleetService.mock(start_time=START)
    assert service.alerts() == []


def test_alerts_aggregates_across_the_fleet() -> None:
    service = FleetService.mock(start_time=START)
    service.advance(2.0, START)
    assert any(alert.type == "ignition_off_movement" for alert in service.alerts())


def test_empty_service_has_no_vehicles_or_alerts() -> None:
    service = FleetService.empty(start_time=START)
    assert service.vehicles() == []
    assert service.alerts() == []


def test_unknown_vehicle_id_returns_none() -> None:
    service = FleetService.mock(start_time=START)
    assert service.vehicle("does-not-exist") is None
