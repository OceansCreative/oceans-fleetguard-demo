"""Builds the production WebSocket connector for the Traccar stream source.

Kept separate from :mod:`app.traccar.stream_source` so the source's consumer
logic carries no dependency on the ``websockets`` library and stays unit-testable
with injected fakes. This module is the only place that talks to a real socket.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from websockets.asyncio.client import connect as ws_connect

from app.traccar.client import TraccarClient
from app.traccar.stream_source import Connect, Frames


def build_ws_connector(client: TraccarClient, ws_url: str) -> Connect:
    """Return a factory that opens an authenticated Traccar WebSocket.

    A fresh session cookie is fetched on every (re)connect so the stream
    re-authenticates cleanly after the server drops or expires the session.
    """

    @asynccontextmanager
    async def _connect() -> AsyncIterator[Frames]:
        # ``session_cookie`` makes a blocking HTTP POST; run it off the event
        # loop so a slow or stalled Traccar login during a (re)connect can't
        # freeze every other task (dashboard broadcasts, ``/health``).
        cookie = await asyncio.to_thread(client.session_cookie)
        async with ws_connect(ws_url, additional_headers={"Cookie": cookie}) as ws:
            yield ws

    return _connect
