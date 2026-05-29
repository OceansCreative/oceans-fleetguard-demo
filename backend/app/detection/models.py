"""Domain models for anti-theft detection.

All models are immutable, dependency-free dataclasses so the detection rules
remain pure functions that are trivial to construct and assert against in tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class GeoPoint:
    """A WGS84 latitude/longitude coordinate in decimal degrees."""

    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class Position:
    """A single normalized vehicle position sample."""

    point: GeoPoint
    speed_mps: float
    course_deg: float
    ignition_on: bool
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class CircularGeofence:
    """A circular allowed area, e.g. a dealership lot or depot."""

    center: GeoPoint
    radius_m: float


@dataclass(frozen=True, slots=True)
class BusinessHours:
    """Operating window during which vehicle movement is expected.

    Attributes:
        operating_days: Weekday indices (Mon=0 .. Sun=6) considered operating.
        start: Inclusive start time of the operating window.
        end: Inclusive end time. If ``end`` is earlier than ``start`` the window
            is treated as crossing midnight (e.g. 22:00 -> 06:00).
    """

    operating_days: frozenset[int]
    start: time
    end: time


class AlertType(StrEnum):
    """The category of a fired theft-detection alert."""

    GEOFENCE_BREACH = "geofence_breach"
    OFF_HOURS_MOVEMENT = "off_hours_movement"
    IGNITION_OFF_MOVEMENT = "ignition_off_movement"
    ABNORMAL_SPEED = "abnormal_speed"
    ABNORMAL_HEADING = "abnormal_heading"


class Severity(StrEnum):
    """How urgently an alert should be surfaced."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Alert:
    """A fired detection signal with a human-readable explanation."""

    type: AlertType
    severity: Severity
    reason: str


@dataclass(frozen=True, slots=True)
class DetectionConfig:
    """Tunable thresholds and reference data for the detection rules.

    Optional fields (``geofence`` / ``business_hours``) disable their respective
    rule when left as ``None``.
    """

    geofence: CircularGeofence | None = None
    business_hours: BusinessHours | None = None
    # Speeds above this (m/s) count as "the vehicle is moving".
    moving_speed_threshold_mps: float = 1.0
    # Speeds above this (m/s) are physically implausible for the fleet.
    max_speed_mps: float = 50.0
    # Course changes above this (degrees) between consecutive samples are
    # treated as abnormal while moving.
    max_heading_change_deg: float = 90.0
