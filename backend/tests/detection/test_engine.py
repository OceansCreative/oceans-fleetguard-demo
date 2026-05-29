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


def _position(**kwargs: object) -> Position:
    defaults: dict[str, object] = {
        "point": DEPOT,
        "speed_mps": 0.0,
        "course_deg": 0.0,
        "ignition_on": True,
        "recorded_at": datetime(2026, 5, 27, 12, 0),
    }
    defaults.update(kwargs)
    return Position(**defaults)  # type: ignore[arg-type]


def test_calm_position_produces_no_alerts() -> None:
    assert detect(_position(), CONFIG) == []


def test_stolen_at_night_trips_multiple_rules() -> None:
    # Far from depot, moving fast, ignition off, at 3am.
    stolen = _position(
        point=GeoPoint(lat=DEPOT.lat + 0.05, lon=DEPOT.lon),
        speed_mps=30.0,
        ignition_on=False,
        recorded_at=datetime(2026, 5, 27, 3, 0),
    )
    alert_types = {alert.type for alert in detect(stolen, CONFIG)}
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
    alert_types = {alert.type for alert in detect(stolen, minimal)}
    assert AlertType.GEOFENCE_BREACH not in alert_types
    assert AlertType.OFF_HOURS_MOVEMENT not in alert_types
    # The always-on ignition rule still fires.
    assert AlertType.IGNITION_OFF_MOVEMENT in alert_types


def test_heading_rule_uses_previous_sample() -> None:
    prev = _position(course_deg=0.0, speed_mps=10.0)
    curr = _position(course_deg=170.0, speed_mps=10.0)
    alert_types = {alert.type for alert in detect(curr, CONFIG, previous=prev)}
    assert AlertType.ABNORMAL_HEADING in alert_types
