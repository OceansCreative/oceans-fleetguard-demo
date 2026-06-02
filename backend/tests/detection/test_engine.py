"""Tests for the detection engine that aggregates the individual rules."""

from __future__ import annotations

from datetime import datetime, time

from app.detection.engine import detect
from app.detection.models import (
    AlertType,
    BusinessHours,
    CircularGeofence,
    DetectionConfig,
    GeoPoint,
    Position,
)

DEPOT = GeoPoint(lat=35.4750, lon=133.0505)
CONFIG = DetectionConfig(
    geofence=CircularGeofence(center=DEPOT, radius_m=500.0),
    business_hours=BusinessHours(
        operating_days=frozenset({0, 1, 2, 3, 4}),
        start=time(9, 0),
        end=time(18, 0),
    ),
    moving_speed_threshold_mps=1.0,
    max_speed_mps=50.0,
    max_heading_change_deg=90.0,
)

# A fixed "wall clock" used by legacy tests — keeps positions fresh so the
# signal-lost rule does not fire unexpectedly.
_NOW = datetime(2026, 5, 27, 12, 0)


def _position(**kwargs: object) -> Position:
    defaults: dict[str, object] = {
        "point": DEPOT,
        "speed_mps": 0.0,
        "course_deg": 0.0,
        "ignition_on": True,
        "recorded_at": _NOW,
    }
    defaults.update(kwargs)
    return Position(**defaults)  # type: ignore[arg-type]


def test_calm_position_produces_no_alerts() -> None:
    assert detect(_position(), CONFIG, now=_NOW) == []


def test_stolen_at_night_trips_multiple_rules() -> None:
    # Far from depot, moving fast, ignition off, at 3am.
    stolen = _position(
        point=GeoPoint(lat=DEPOT.lat + 0.05, lon=DEPOT.lon),
        speed_mps=30.0,
        ignition_on=False,
        recorded_at=datetime(2026, 5, 27, 3, 0),
    )
    # Pass now == recorded_at so signal-lost does not fire alongside the others.
    now = datetime(2026, 5, 27, 3, 0)
    alert_types = {alert.type for alert in detect(stolen, CONFIG, now=now)}
    assert AlertType.GEOFENCE_BREACH in alert_types
    assert AlertType.OFF_HOURS_MOVEMENT in alert_types
    assert AlertType.IGNITION_OFF_MOVEMENT in alert_types


def test_disabled_optional_rules_are_skipped() -> None:
    minimal = DetectionConfig()  # no geofence, no business hours
    stolen = _position(
        point=GeoPoint(lat=DEPOT.lat + 0.05, lon=DEPOT.lon),
        speed_mps=30.0,
        ignition_on=False,
        recorded_at=datetime(2026, 5, 27, 3, 0),
    )
    now = datetime(2026, 5, 27, 3, 0)
    alert_types = {alert.type for alert in detect(stolen, minimal, now=now)}
    assert AlertType.GEOFENCE_BREACH not in alert_types
    assert AlertType.OFF_HOURS_MOVEMENT not in alert_types
    # The always-on ignition rule still fires.
    assert AlertType.IGNITION_OFF_MOVEMENT in alert_types


def test_heading_rule_uses_previous_sample() -> None:
    prev = _position(course_deg=0.0, speed_mps=10.0)
    curr = _position(course_deg=170.0, speed_mps=10.0)
    alert_types = {
        alert.type for alert in detect(curr, CONFIG, previous=prev, now=_NOW)
    }
    assert AlertType.ABNORMAL_HEADING in alert_types


def test_signal_lost_participates_in_full_detection_pass() -> None:
    # Position recorded 20 minutes ago; now is 20 min later → 1200 s silence.
    recorded = datetime(2026, 5, 27, 12, 0)
    now = datetime(2026, 5, 27, 12, 20)
    pos = _position(recorded_at=recorded)
    alert_types = {alert.type for alert in detect(pos, CONFIG, now=now)}
    assert AlertType.SIGNAL_LOST in alert_types


def test_signal_lost_absent_when_position_is_fresh() -> None:
    # Position recorded just 1 minute ago; well within default 600 s window.
    recorded = datetime(2026, 5, 27, 12, 0)
    now = datetime(2026, 5, 27, 12, 1)
    pos = _position(recorded_at=recorded)
    alert_types = {alert.type for alert in detect(pos, CONFIG, now=now)}
    assert AlertType.SIGNAL_LOST not in alert_types


def test_detect_defaults_now_for_signal_lost() -> None:
    # Without an explicit `now`, the engine falls back to datetime.utcnow() (naive).
    # A position recorded just now (also naive UTC) should not trigger signal-lost.
    pos = _position(recorded_at=datetime.utcnow())
    alert_types = {alert.type for alert in detect(pos, CONFIG)}
    assert AlertType.SIGNAL_LOST not in alert_types
