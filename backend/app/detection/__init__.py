"""Anti-theft detection: pure, testable rules over normalized positions."""

from __future__ import annotations

from app.detection.engine import detect
from app.detection.models import (
    Alert,
    AlertType,
    BusinessHours,
    CircularGeofence,
    DetectionConfig,
    GeoPoint,
    Position,
    Severity,
)

__all__ = [
    "Alert",
    "AlertType",
    "BusinessHours",
    "CircularGeofence",
    "DetectionConfig",
    "GeoPoint",
    "Position",
    "Severity",
    "detect",
]
