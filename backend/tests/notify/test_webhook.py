"""Tests for the CRITICAL-alert webhook notifier."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.api.schemas import AlertOut, PositionOut, VehicleOut
from app.notify.webhook import CriticalAlertNotifier


def _vehicle(*, vid: str = "v-1", alerts: list[AlertOut]) -> VehicleOut:
    return VehicleOut(
        id=vid,
        name="Van 01",
        plate="matsue-001",
        position=PositionOut(
            lat=35.5,
            lon=133.1,
            speed_mps=12.0,
            course_deg=90.0,
            ignition_on=False,
            recorded_at=datetime(2026, 1, 1, 3, 0, tzinfo=UTC),
        ),
        geofence=None,
        alerts=alerts,
    )


def _critical(reason: str = "moving with ignition off") -> AlertOut:
    return AlertOut(type="ignition_off_movement", severity="critical", reason=reason)


def _warning() -> AlertOut:
    return AlertOut(type="abnormal_speed", severity="warning", reason="fast")


class _Capture:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def __call__(self, url: str, payload: dict[str, Any]) -> None:
        self.events.append(payload)


def test_disabled_when_no_url() -> None:
    capture = _Capture()
    notifier = CriticalAlertNotifier("", sender=capture)
    asyncio.run(notifier.process([_vehicle(alerts=[_critical()])]))
    assert capture.events == []


def test_fires_on_a_new_critical_alert() -> None:
    capture = _Capture()
    notifier = CriticalAlertNotifier("https://hook.test/x", sender=capture)
    asyncio.run(notifier.process([_vehicle(alerts=[_critical()])]))
    assert len(capture.events) == 1
    event = capture.events[0]
    assert event["event"] == "critical_alert"
    assert event["vehicle"]["id"] == "v-1"
    assert event["alert"]["severity"] == "critical"
    assert event["position"]["lat"] == 35.5


def test_ignores_non_critical_alerts() -> None:
    capture = _Capture()
    notifier = CriticalAlertNotifier("https://hook.test/x", sender=capture)
    asyncio.run(notifier.process([_vehicle(alerts=[_warning()])]))
    assert capture.events == []


def test_deduplicates_a_persistent_alert() -> None:
    capture = _Capture()
    notifier = CriticalAlertNotifier("https://hook.test/x", sender=capture)
    asyncio.run(notifier.process([_vehicle(alerts=[_critical()])]))
    asyncio.run(notifier.process([_vehicle(alerts=[_critical()])]))
    assert len(capture.events) == 1  # fired once, not on every tick


def test_refires_after_clearing_and_recurring() -> None:
    capture = _Capture()
    notifier = CriticalAlertNotifier("https://hook.test/x", sender=capture)
    asyncio.run(notifier.process([_vehicle(alerts=[_critical()])]))
    asyncio.run(notifier.process([_vehicle(alerts=[])]))  # condition cleared
    asyncio.run(notifier.process([_vehicle(alerts=[_critical()])]))  # recurred
    assert len(capture.events) == 2
