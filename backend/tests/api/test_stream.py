"""Tests for the WebSocket fleet streamer."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from app.api.fleet_service import FleetService
from app.api.stream import FleetStreamer
from app.config import Settings
from app.main import create_app
from fastapi import WebSocket
from fastapi.testclient import TestClient


def test_websocket_sends_an_initial_snapshot() -> None:
    settings = Settings(
        mock_mode=True,
        cors_origins=("http://localhost:3000",),
        traccar_base_url="http://traccar:8082",
        traccar_ws_url="ws://traccar:8082/api/socket",
        traccar_username="",
        traccar_password="",
        traccar_transport="ws",
    )
    with (
        TestClient(create_app(settings)) as client,
        client.websocket_connect("/ws/positions") as websocket,
    ):
        message = websocket.receive_json()
        assert "vehicles" in message
        assert len(message["vehicles"]) == 5


class _FakeWebSocket:
    """Minimal stand-in capturing or failing ``send_json`` calls."""

    def __init__(self, *, fail: bool) -> None:
        self._fail = fail
        self.sent: list[Any] = []

    async def send_json(self, payload: Any) -> None:
        if self._fail:
            raise RuntimeError("client gone")
        self.sent.append(payload)


def test_broadcast_drops_clients_that_error() -> None:
    streamer = FleetStreamer(FleetService.mock())
    healthy = _FakeWebSocket(fail=False)
    broken = _FakeWebSocket(fail=True)
    streamer._clients.update(  # noqa: SLF001 - exercising broadcast directly
        {cast(WebSocket, healthy), cast(WebSocket, broken)}
    )

    asyncio.run(streamer._broadcast())  # noqa: SLF001

    assert healthy.sent  # healthy client received the payload
    assert cast(WebSocket, broken) not in streamer._clients  # broken one dropped


class _FlakyService:
    """A fleet service whose ``advance`` always raises, counting its calls."""

    def __init__(self) -> None:
        self.ticks = 0

    def advance(self, step_s: float) -> None:
        self.ticks += 1
        raise RuntimeError("upstream boom")

    def vehicles(self) -> list[Any]:
        return []


def test_broadcast_loop_survives_a_failing_tick() -> None:
    # A raising advance() must not kill the stream task: the loop logs and keeps
    # ticking, so the live feed recovers once the upstream does.
    service = _FlakyService()
    streamer = FleetStreamer(cast(FleetService, service), interval_s=0.0, step_s=0.0)

    async def scenario() -> int:
        streamer.start()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 2.0  # generous bound; ticks are sub-millisecond
        while service.ticks < 3 and loop.time() < deadline:
            await asyncio.sleep(0.01)
        await streamer.stop()
        return service.ticks

    assert asyncio.run(scenario()) >= 3  # kept ticking past repeated failures
