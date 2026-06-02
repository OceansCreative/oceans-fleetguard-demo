"""Aggregate the individual detection rules into a single evaluation pass."""

from __future__ import annotations

from datetime import datetime

from app.detection.models import Alert, DetectionConfig, Position
from app.detection.rules import (
    check_abnormal_heading,
    check_abnormal_speed,
    check_geofence_breach,
    check_ignition_off_movement,
    check_off_hours_movement,
    check_signal_lost,
)


def detect(
    current: Position,
    config: DetectionConfig,
    previous: Position | None = None,
    now: datetime | None = None,
) -> list[Alert]:
    """Run every enabled rule against a position and collect the alerts.

    Args:
        current: The latest position sample.
        config: Thresholds and reference data; ``None`` fields disable rules.
        previous: The prior sample, required only by the heading rule.
        now: Reference wall-clock time for the signal-lost rule.  Must share
            timezone-awareness with the positions' ``recorded_at`` timestamps.
            When omitted the caller is responsible for ensuring the source
            positions carry naive UTC timestamps; production callers should
            supply an explicit tz-aware ``now``.

    Returns:
        Alerts in a stable order, empty when nothing tripped.
    """
    effective_now: datetime = now if now is not None else datetime.utcnow()

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
    candidates.append(
        check_signal_lost(current, effective_now, config.max_signal_silence_s)
    )

    return [alert for alert in candidates if alert is not None]
