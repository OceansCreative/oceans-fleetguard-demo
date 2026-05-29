"""Tests for the production WebSocket connector factory."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
from app.traccar import connect as connect_module
from app.traccar.connect import build_ws_connector

from tests.traccar._helpers import build_client


async def _no_frames() -> AsyncIterator[str]:
    return
    yield ""  # pragma: no cover - makes this an async generator


def _session_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/session":
        return httpx.Response(
            200, headers={"Set-Cookie": "JSESSIONID=abc123; Path=/"}, json={"id": 1}
        )
    return httpx.Response(404)


def test_connector_authenticates_then_opens_socket_with_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_ws_connect(url: str, *, additional_headers: dict[str, str]) -> Any:
        @asynccontextmanager
        async def _cm() -> AsyncIterator[AsyncIterator[str]]:
            captured["url"] = url
            captured["headers"] = dict(additional_headers)
            yield _no_frames()

        return _cm()

    monkeypatch.setattr(connect_module, "ws_connect", fake_ws_connect)

    async def scenario() -> None:
        client = build_client(_session_handler)
        connect = build_ws_connector(client, "ws://traccar.test/api/socket")
        async with connect():
            pass

    asyncio.run(scenario())

    assert captured["url"] == "ws://traccar.test/api/socket"
    assert captured["headers"]["Cookie"] == "JSESSIONID=abc123"
