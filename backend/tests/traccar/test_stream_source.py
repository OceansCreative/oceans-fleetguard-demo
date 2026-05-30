"""Tests for the WebSocket-backed Traccar stream source."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from app.traccar.client import TraccarClient
from app.traccar.normalize import roster_from_devices
from app.traccar.stream_source import TraccarStreamSource

from tests.traccar._helpers import (
    DEVICE_TRUCK,
    DEVICE_VAN,
    POSITION_VAN,
    build_client,
    static_handler,
)


def _frame(positions: list[dict[str, Any]]) -> str:
    return json.dumps({"positions": positions})


class _FakeFrames:
    """An async context manager + iterator that replays canned frames.

    After the canned frames are exhausted it optionally parks on ``park`` so the
    "connection" stays open (mimicking a live socket) until the task is
    cancelled, instead of closing and triggering a reconnect.
    """

    def __init__(self, frames: list[str], park: asyncio.Event | None = None) -> None:
        self._frames = list(frames)
        self._park = park

    async def __aenter__(self) -> _FakeFrames:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def __aiter__(self) -> _FakeFrames:
        return self

    async def __anext__(self) -> str:
        if self._frames:
            return self._frames.pop(0)
        if self._park is not None:
            await self._park.wait()
        raise StopAsyncIteration


def _source_with_van_roster(connect: Any) -> TraccarStreamSource:
    source = TraccarStreamSource(
        build_client(static_handler([DEVICE_VAN], [])), connect
    )
    source._roster = roster_from_devices([DEVICE_VAN])
    return source


def test_consume_applies_frames_and_tracks_previous() -> None:
    source = _source_with_van_roster(connect=lambda: _FakeFrames([]))
    moved = {**POSITION_VAN, "course": 123.0, "fixTime": "2026-05-29T03:05:00Z"}
    frames = _FakeFrames([_frame([POSITION_VAN]), _frame([moved])])

    asyncio.run(source._consume(frames))

    van = source.snapshot()[0]
    assert van.vehicle.name == "Van 01"
    assert van.current.course_deg == 123.0
    assert van.previous is not None
    assert van.previous.course_deg == 90.0


def test_consume_skips_malformed_and_positionless_frames() -> None:
    source = _source_with_van_roster(connect=lambda: _FakeFrames([]))
    frames = _FakeFrames(
        [
            "this is not json",
            json.dumps({"devices": [DEVICE_VAN]}),
            _frame([POSITION_VAN]),
        ]
    )

    asyncio.run(source._consume(frames))

    assert {s.vehicle.id for s in source.snapshot()} == {"1"}


def test_start_primes_roster_and_streams_until_closed() -> None:
    park = asyncio.Event()

    async def scenario() -> tuple[list[str], bool]:
        source = TraccarStreamSource(
            build_client(static_handler([DEVICE_VAN], [])),
            connect=lambda: _FakeFrames([_frame([POSITION_VAN])], park=park),
        )
        await source.start()
        # Let the background task connect and process the queued frame.
        for _ in range(5):
            await asyncio.sleep(0)
        names = [s.vehicle.name for s in source.snapshot()]
        await source.aclose()
        return names, source._task is None

    names, closed = asyncio.run(scenario())
    assert names == ["Van 01"]  # roster primed over REST, position from the stream
    assert closed


def test_run_reconnects_after_a_stream_error() -> None:
    park = asyncio.Event()
    state = {"attempts": 0}

    def connect() -> _FakeFrames:
        state["attempts"] += 1
        if state["attempts"] == 1:
            raise ConnectionError("socket dropped")
        return _FakeFrames([_frame([POSITION_VAN])], park=park)

    async def scenario() -> list[str]:
        source = TraccarStreamSource(
            build_client(static_handler([DEVICE_VAN], [])),
            connect,
            reconnect_delay_s=0.0,
        )
        await source.start()
        for _ in range(20):
            await asyncio.sleep(0)
            if source.snapshot():
                break
        names = [s.vehicle.name for s in source.snapshot()]
        await source.aclose()
        return names

    assert asyncio.run(scenario()) == ["Van 01"]
    assert state["attempts"] >= 2  # failed once, then reconnected


def test_aclose_before_start_is_safe() -> None:
    source = TraccarStreamSource(
        build_client(static_handler([DEVICE_VAN], [])), connect=lambda: _FakeFrames([])
    )
    asyncio.run(source.aclose())  # no background task yet; must not raise
    assert source.snapshot() == []


def test_roster_is_refreshed_after_startup() -> None:
    park = asyncio.Event()
    devices = [DEVICE_VAN]  # the roster Traccar serves; grows mid-run below

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/devices":
            return httpx.Response(200, json=devices)
        return httpx.Response(200, json=[])  # positions/geofences unused here

    client = TraccarClient(
        "http://traccar.test",
        "demo",
        "secret",
        client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="http://traccar.test"
        ),
    )

    async def scenario() -> set[str]:
        source = TraccarStreamSource(
            client,
            connect=lambda: _FakeFrames([], park=park),
            roster_refresh_interval_s=0.0,  # refresh as fast as the loop allows
        )
        await source.start()
        assert set(source._roster) == {"1"}  # only the van at startup
        devices.append(DEVICE_TRUCK)  # a vehicle appears after launch
        for _ in range(50):
            await asyncio.sleep(0.01)
            if set(source._roster) == {"1", "2"}:
                break
        roster = set(source._roster)
        await source.aclose()
        return roster

    # The periodic refresh must pick up the newly added vehicle.
    assert asyncio.run(scenario()) == {"1", "2"}


def test_start_tolerates_a_failed_roster_fetch() -> None:
    park = asyncio.Event()

    def failing_devices(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"})

    async def scenario() -> list[str]:
        source = TraccarStreamSource(
            build_client(failing_devices),
            connect=lambda: _FakeFrames([_frame([POSITION_VAN])], park=park),
        )
        await source.start()  # roster fetch fails internally, but start succeeds
        for _ in range(5):
            await asyncio.sleep(0)
        ids = [s.vehicle.id for s in source.snapshot()]
        await source.aclose()
        return ids

    # Position still surfaces via the fallback identity despite the empty roster.
    assert asyncio.run(scenario()) == ["1"]
