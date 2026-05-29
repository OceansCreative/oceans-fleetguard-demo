"""Anti-theft detection rules, each a small pure function.

Every rule takes explicit inputs and returns an :class:`Alert` when it trips or
``None`` otherwise. No I/O, no globals — so each rule is exhaustively testable.
"""

from __future__ import annotations

from datetime import datetime

from app.detection.geo import angular_difference_deg, haversine_m
from app.detection.models import (
    Alert,
    AlertType,
    BusinessHours,
    CircularGeofence,
    Position,
    Severity,
)


def check_geofence_breach(
    position: Position, geofence: CircularGeofence
) -> Alert | None:
    """Fire when the vehicle is outside its allowed circular area."""
    distance = haversine_m(position.point, geofence.center)
    if distance <= geofence.radius_m:
        return None
    overshoot = distance - geofence.radius_m
    return Alert(
        type=AlertType.GEOFENCE_BREACH,
        severity=Severity.CRITICAL,
        reason=f"{overshoot:.0f} m outside the {geofence.radius_m:.0f} m geofence",
    )


def is_within_business_hours(moment: datetime, hours: BusinessHours) -> bool:
    """Return whether ``moment`` falls inside the operating window."""
    if moment.weekday() not in hours.operating_days:
        return False
    now = moment.time()
    if hours.start <= hours.end:
        return hours.start <= now <= hours.end
    # Window crosses midnight (e.g. 22:00 -> 06:00).
    return now >= hours.start or now <= hours.end


def check_off_hours_movement(
    position: Position, hours: BusinessHours, moving_threshold_mps: float
) -> Alert | None:
    """Fire when the vehicle moves outside business / operating hours."""
    if position.speed_mps <= moving_threshold_mps:
        return None
    if is_within_business_hours(position.recorded_at, hours):
        return None
    return Alert(
        type=AlertType.OFF_HOURS_MOVEMENT,
        severity=Severity.WARNING,
        reason=f"moving at {position.speed_mps:.1f} m/s outside business hours",
    )


def check_ignition_off_movement(
    position: Position, moving_threshold_mps: float
) -> Alert | None:
    """Fire when the vehicle moves while its ignition is reported OFF."""
    if position.ignition_on or position.speed_mps <= moving_threshold_mps:
        return None
    return Alert(
        type=AlertType.IGNITION_OFF_MOVEMENT,
        severity=Severity.CRITICAL,
        reason=f"moving at {position.speed_mps:.1f} m/s with ignition off",
    )


def check_abnormal_speed(position: Position, max_speed_mps: float) -> Alert | None:
    """Fire when the reported speed exceeds a plausible maximum."""
    if position.speed_mps <= max_speed_mps:
        return None
    return Alert(
        type=AlertType.ABNORMAL_SPEED,
        severity=Severity.WARNING,
        reason=f"speed {position.speed_mps:.1f} m/s exceeds max {max_speed_mps:.1f}",
    )


def check_abnormal_heading(
    previous: Position | None,
    current: Position,
    max_change_deg: float,
    moving_threshold_mps: float,
) -> Alert | None:
    """Fire on an implausibly sharp course change between two moving samples."""
    if previous is None or current.speed_mps <= moving_threshold_mps:
        return None
    change = angular_difference_deg(previous.course_deg, current.course_deg)
    if change <= max_change_deg:
        return None
    return Alert(
        type=AlertType.ABNORMAL_HEADING,
        severity=Severity.INFO,
        reason=f"heading changed {change:.0f}° (> {max_change_deg:.0f}°)",
    )
