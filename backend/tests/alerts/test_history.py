"""Tests for AlertHistory — the in-memory, bounded alert activation log."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.alerts.history import AlertHistory
from app.api.schemas import AlertOut, PositionOut, VehicleOut
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _make_dt(second: int = 0) -> datetime:
    return datetime(2026, 1, 1, 12, 0, second, tzinfo=UTC)


def _vehicle(
    *,
    vid: str = "v-1",
    name: str = "Van 01",
    alerts: list[AlertOut],
    recorded_at: datetime | None = None,
) -> VehicleOut:
    return VehicleOut(
        id=vid,
        name=name,
        plate="matsue-001",
        position=PositionOut(
            lat=35.5,
            lon=133.1,
            speed_mps=12.0,
            course_deg=90.0,
            ignition_on=False,
            recorded_at=recorded_at or _make_dt(),
        ),
        geofence=None,
        alerts=alerts,
    )


def _critical(reason: str = "moving with ignition off") -> AlertOut:
    return AlertOut(type="ignition_off_movement", severity="critical", reason=reason)


def _warning() -> AlertOut:
    return AlertOut(type="abnormal_speed", severity="warning", reason="speeding")


def _clock(ts: datetime) -> datetime:
    return ts


# ---------------------------------------------------------------------------
# Unit tests for AlertHistory
# ---------------------------------------------------------------------------


def test_fires_once_on_new_alert() -> None:
    tick = [_make_dt(0)]

    def clock() -> datetime:
        return tick[0]

    h = AlertHistory(now=clock)
    h.record([_vehicle(alerts=[_critical()])])
    assert len(h.entries()) == 1
    entry = h.entries()[0]
    assert entry.vehicle_id == "v-1"
    assert entry.alert_type == "ignition_off_movement"
    assert entry.alert_severity == "critical"


def test_deduplicates_ongoing_alert() -> None:
    h = AlertHistory()
    h.record([_vehicle(alerts=[_critical()])])
    h.record([_vehicle(alerts=[_critical()])])
    assert len(h.entries()) == 1


def test_refires_after_clear_and_recur() -> None:
    h = AlertHistory()
    h.record([_vehicle(alerts=[_critical()])])
    h.record([_vehicle(alerts=[])])  # cleared
    h.record([_vehicle(alerts=[_critical()])])  # recurred
    assert len(h.entries()) == 2


def test_records_non_critical_alerts() -> None:
    h = AlertHistory()
    h.record([_vehicle(alerts=[_warning()])])
    assert len(h.entries()) == 1
    assert h.entries()[0].alert_severity == "warning"


def test_records_all_severities_independently() -> None:
    h = AlertHistory()
    h.record([_vehicle(alerts=[_critical(), _warning()])])
    assert len(h.entries()) == 2
    severities = {e.alert_severity for e in h.entries()}
    assert severities == {"critical", "warning"}


def test_maxlen_drops_oldest() -> None:
    h = AlertHistory(maxlen=3)
    # Alternate vehicles so each tick has a new (vehicle_id, alert_type) key.
    for i in range(5):
        h.record([_vehicle(vid=f"v-{i}", alerts=[_critical()])])
    entries = h.entries()
    assert len(entries) == 3
    # Newest first — last three vehicles recorded
    ids = {e.vehicle_id for e in entries}
    assert "v-0" not in ids
    assert "v-1" not in ids


def test_entries_newest_first() -> None:
    times = [_make_dt(i) for i in range(3)]
    idx = [0]

    def clock() -> datetime:
        t = times[idx[0]]
        idx[0] += 1
        return t

    h = AlertHistory(now=clock)
    for i in range(3):
        h.record([_vehicle(vid=f"v-{i}", alerts=[_critical()])])

    entries = h.entries()
    assert entries[0].vehicle_id == "v-2"
    assert entries[1].vehicle_id == "v-1"
    assert entries[2].vehicle_id == "v-0"


def test_entries_limit() -> None:
    h = AlertHistory()
    for i in range(5):
        h.record([_vehicle(vid=f"v-{i}", alerts=[_critical()])])
    assert len(h.entries(limit=2)) == 2


def test_entries_limit_larger_than_buffer() -> None:
    h = AlertHistory()
    h.record([_vehicle(alerts=[_critical()])])
    assert len(h.entries(limit=100)) == 1


def test_recorded_at_uses_injected_clock() -> None:
    fixed = _make_dt(42)
    h = AlertHistory(now=lambda: fixed)
    h.record([_vehicle(alerts=[_critical()])])
    assert h.entries()[0].recorded_at == fixed


# ---------------------------------------------------------------------------
# App-level integration test
# ---------------------------------------------------------------------------


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


def test_get_alert_history_returns_empty_list_initially() -> None:
    """Fresh app → history is empty (no ticks have fired yet)."""
    client = TestClient(create_app(_settings()))
    response = client.get("/api/alerts/history")
    assert response.status_code == 200
    assert response.json() == []


def test_get_alert_history_limit_query_param_validation() -> None:
    """limit=0 is rejected (ge=1 constraint)."""
    client = TestClient(create_app(_settings()))
    response = client.get("/api/alerts/history?limit=0")
    assert response.status_code == 422


def test_get_alert_history_limit_too_large_rejected() -> None:
    """limit > 500 is rejected (le=500 constraint)."""
    client = TestClient(create_app(_settings()))
    response = client.get("/api/alerts/history?limit=501")
    assert response.status_code == 422


def test_get_alert_history_valid_limit_accepted() -> None:
    """Valid limit query param returns a list."""
    client = TestClient(create_app(_settings()))
    response = client.get("/api/alerts/history?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.parametrize("limit", [1, 50, 500])
def test_get_alert_history_limit_boundary_values(limit: int) -> None:
    client = TestClient(create_app(_settings()))
    response = client.get(f"/api/alerts/history?limit={limit}")
    assert response.status_code == 200
