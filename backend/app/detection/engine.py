"""Aggregate the individual detection rules into a single evaluation pass."""

from __future__ import annotations

from app.detection.models import Alert, DetectionConfig, Position
from app.detection.rules import (
    check_abnormal_heading,
    check_abnormal_speed,
    check_geofence_breach,
    check_ignition_off_movement,
    check_off_hours_movement,
)


def detect(
    current: Position,
    config: DetectionConfig,
    previous: Position | None = None,
) -> list[Alert]:
    """Run every enabled rule against a position and collect the alerts.

    Args:
        current: The latest position sample.
        config: Thresholds and reference data; ``None`` fields disable rules.
        previous: The prior sample, required only by the heading rule.

    Returns:
        Alerts in a stable order, empty when nothing tripped.
    """
    candidates: list[Alert | None] = []

    if config.geofence is not None:
        candidates.append(check_geofence_breach(current, config.geofence))
    if config.business_hours is not None:
        candidates.append(
            check_off_hours_movement(
                current, config.business_hours, config.moving_speed_threshold_mps
            )
        )
    candidates.append(
        check_ignition_off_movement(current, config.moving_speed_threshold_mps)
    )
    candidates.append(check_abnormal_speed(current, config.max_speed_mps))
    candidates.append(
        check_abnormal_heading(
            previous,
            current,
            config.max_heading_change_deg,
            config.moving_speed_threshold_mps,
        )
    )

    return [alert for alert in candidates if alert is not None]
