"""Boundary and abnormal-case coverage for each detection rule."""

from __future__ import annotations

from datetime import datetime, time

import pytest
from app.detection.models import (
    AlertType,
    BusinessHours,
    CircularGeofence,
    GeoPoint,
    Position,
    Severity,
)
from app.detection.rules import (
    check_abnormal_heading,
    check_abnormal_speed,
    check_geofence_breach,
    check_ignition_off_movement,
    check_off_hours_movement,
    is_within_business_hours,
)

DEPOT = GeoPoint(lat=35.4750, lon=133.0505)
GEOFENCE = CircularGeofence(center=DEPOT, radius_m=500.0)
WEEKDAYS = frozenset({0, 1, 2, 3, 4})
HOURS = BusinessHours(operating_days=WEEKDAYS, start=time(9, 0), end=time(18, 0))
OVERNIGHT = BusinessHours(
    operating_days=frozenset(range(7)), start=time(22, 0), end=time(6, 0)
)


def _position(
    *,
    point: GeoPoint = DEPOT,
    speed_mps: float = 0.0,
    course_deg: float = 0.0,
    ignition_on: bool = True,
    recorded_at: datetime = datetime(2026, 5, 27, 12, 0),  # a Wednesday noon
) -> Position:
    return Position(
        point=point,
        speed_mps=speed_mps,
        course_deg=course_deg,
        ignition_on=ignition_on,
        recorded_at=recorded_at,
    )


# --- geofence -------------------------------------------------------------


def test_geofence_inside_does_not_alert() -> None:
    assert check_geofence_breach(_position(), GEOFENCE) is None


def test_geofence_just_outside_alerts_critical() -> None:
    # ~1.2 km north of the depot, well beyond the 500 m radius.
    far = _position(point=GeoPoint(lat=DEPOT.lat + 0.011, lon=DEPOT.lon))
    alert = check_geofence_breach(far, GEOFENCE)
    assert alert is not None
    assert alert.type is AlertType.GEOFENCE_BREACH
    assert alert.severity is Severity.CRITICAL


def test_geofence_point_at_center_is_inside() -> None:
    assert check_geofence_breach(_position(point=DEPOT), GEOFENCE) is None


# --- business hours -------------------------------------------------------


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (datetime(2026, 5, 27, 9, 0), True),  # Wed, exactly at start (inclusive)
        (datetime(2026, 5, 27, 18, 0), True),  # exactly at end (inclusive)
        (datetime(2026, 5, 27, 8, 59), False),  # one minute before
        (datetime(2026, 5, 27, 18, 1), False),  # one minute after
        (datetime(2026, 5, 30, 12, 0), False),  # Saturday, non-operating day
    ],
)
def test_is_within_business_hours(moment: datetime, expected: bool) -> None:
    assert is_within_business_hours(moment, HOURS) is expected


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (datetime(2026, 5, 27, 23, 0), True),  # inside overnight window
        (datetime(2026, 5, 27, 5, 0), True),  # early morning still inside
        (datetime(2026, 5, 27, 12, 0), False),  # midday is outside
    ],
)
def test_is_within_overnight_window(moment: datetime, expected: bool) -> None:
    assert is_within_business_hours(moment, OVERNIGHT) is expected


def test_off_hours_movement_alerts_when_moving_at_night() -> None:
    night = _position(speed_mps=15.0, recorded_at=datetime(2026, 5, 27, 2, 0))
    alert = check_off_hours_movement(night, HOURS, moving_threshold_mps=1.0)
    assert alert is not None
    assert alert.type is AlertType.OFF_HOURS_MOVEMENT


def test_off_hours_movement_silent_when_stationary() -> None:
    parked = _position(speed_mps=0.5, recorded_at=datetime(2026, 5, 27, 2, 0))
    assert check_off_hours_movement(parked, HOURS, moving_threshold_mps=1.0) is None


def test_off_hours_movement_silent_during_business_hours() -> None:
    daytime = _position(speed_mps=15.0, recorded_at=datetime(2026, 5, 27, 12, 0))
    assert check_off_hours_movement(daytime, HOURS, moving_threshold_mps=1.0) is None


# --- ignition off ---------------------------------------------------------


def test_ignition_off_movement_alerts_critical() -> None:
    rolling = _position(speed_mps=5.0, ignition_on=False)
    alert = check_ignition_off_movement(rolling, moving_threshold_mps=1.0)
    assert alert is not None
    assert alert.severity is Severity.CRITICAL


def test_ignition_off_but_stationary_is_silent() -> None:
    parked = _position(speed_mps=0.0, ignition_on=False)
    assert check_ignition_off_movement(parked, moving_threshold_mps=1.0) is None


def test_ignition_on_while_moving_is_silent() -> None:
    driving = _position(speed_mps=20.0, ignition_on=True)
    assert check_ignition_off_movement(driving, moving_threshold_mps=1.0) is None


def test_ignition_off_movement_at_threshold_is_silent() -> None:
    at_threshold = _position(speed_mps=1.0, ignition_on=False)
    assert check_ignition_off_movement(at_threshold, moving_threshold_mps=1.0) is None


# --- abnormal speed -------------------------------------------------------


def test_abnormal_speed_alerts_above_max() -> None:
    fast = _position(speed_mps=60.0)
    alert = check_abnormal_speed(fast, max_speed_mps=50.0)
    assert alert is not None
    assert alert.type is AlertType.ABNORMAL_SPEED


def test_abnormal_speed_at_max_is_silent() -> None:
    assert check_abnormal_speed(_position(speed_mps=50.0), max_speed_mps=50.0) is None


# --- abnormal heading -----------------------------------------------------


def test_abnormal_heading_alerts_on_sharp_turn_while_moving() -> None:
    prev = _position(course_deg=0.0, speed_mps=10.0)
    curr = _position(course_deg=170.0, speed_mps=10.0)
    alert = check_abnormal_heading(
        prev, curr, max_change_deg=90.0, moving_threshold_mps=1.0
    )
    assert alert is not None
    assert alert.type is AlertType.ABNORMAL_HEADING


def test_abnormal_heading_silent_without_previous_sample() -> None:
    curr = _position(course_deg=170.0, speed_mps=10.0)
    assert (
        check_abnormal_heading(
            None, curr, max_change_deg=90.0, moving_threshold_mps=1.0
        )
        is None
    )


def test_abnormal_heading_silent_when_nearly_stationary() -> None:
    prev = _position(course_deg=0.0, speed_mps=0.2)
    curr = _position(course_deg=180.0, speed_mps=0.2)
    assert (
        check_abnormal_heading(
            prev, curr, max_change_deg=90.0, moving_threshold_mps=1.0
        )
        is None
    )


def test_abnormal_heading_at_threshold_is_silent() -> None:
    prev = _position(course_deg=0.0, speed_mps=10.0)
    curr = _position(course_deg=90.0, speed_mps=10.0)
    assert (
        check_abnormal_heading(
            prev, curr, max_change_deg=90.0, moving_threshold_mps=1.0
        )
        is None
    )
