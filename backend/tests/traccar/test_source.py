"""Tests for the Traccar-backed fleet source (poll + previous tracking)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
from app.traccar.source import TraccarSource

from tests.traccar._helpers import (
    DEVICE_VAN,
    DEVICES,
    GEOFENCES,
    POSITION_VAN,
    POSITIONS,
    build_client,
    static_handler,
)

NOW = datetime(2026, 5, 29, 3, 0, tzinfo=UTC)


def test_snapshot_lazily_polls_on_first_read() -> None:
    source = TraccarSource(build_client(static_handler(DEVICES, POSITIONS)))
    samples = source.snapshot()
    assert {s.vehicle.id for s in samples} == {"1", "2"}
    assert all(s.previous is None for s in samples)  # no history on first poll
    asyncio.run(source.aclose())


def test_consecutive_polls_carry_the_previous_position_forward() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/devices":
            return httpx.Response(200, json=[DEVICE_VAN])
        if request.url.path == "/api/geofences":
            return httpx.Response(200, json=[])
        calls["n"] += 1
        moved = {
            **POSITION_VAN,
            "course": float(calls["n"]),
            "fixTime": f"2026-05-29T03:0{calls['n']}:00Z",
        }
        return httpx.Response(200, json=[moved])

    source = TraccarSource(build_client(handler))
    source.advance(2.0, NOW)  # poll 1
    source.advance(2.0, NOW)  # poll 2
    van = source.snapshot()[0]
    assert van.previous is not None
    assert van.previous.course_deg == 1.0
    assert van.current.course_deg == 2.0
    asyncio.run(source.aclose())


def test_failed_poll_keeps_the_last_good_snapshot() -> None:
    state = {"fail": False}

    def handler(request: httpx.Request) -> httpx.Response:
        if state["fail"]:
            return httpx.Response(503, json={"error": "down"})
        if request.url.path == "/api/devices":
            return httpx.Response(200, json=DEVICES)
        return httpx.Response(200, json=POSITIONS)

    source = TraccarSource(build_client(handler))
    source.advance(2.0, NOW)  # good poll
    assert len(source.snapshot()) == 2

    state["fail"] = True
    source.advance(2.0, NOW)  # upstream now failing
    assert len(source.snapshot()) == 2  # last good snapshot retained
    asyncio.run(source.aclose())


def test_poll_attaches_circular_geofences_to_vehicles() -> None:
    source = TraccarSource(build_client(static_handler(DEVICES, POSITIONS, GEOFENCES)))
    source.advance(2.0, NOW)
    van = next(s for s in source.snapshot() if s.vehicle.id == "1")
    assert van.vehicle.geofence is not None  # assigned via geofenceIds
    assert van.vehicle.geofence.radius_m == 500.0
    asyncio.run(source.aclose())
