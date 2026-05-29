"""A push-based :class:`FleetSource` backed by Traccar's WebSocket feed.

Traccar streams updates over ``ws://<host>/api/socket`` once authenticated.
This source runs a background task that consumes those frames and folds them
into an in-memory cache via the pure helpers in :mod:`app.traccar.normalize`;
:meth:`snapshot` just reads that cache, so REST reads stay cheap and never
touch the network. The device roster (names/plates) is primed once over REST,
since the socket frames carry only positions and status.

The WebSocket connection is supplied as an injected ``connect`` factory, which
keeps the source decoupled from a real server: tests feed it canned frames.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime

from app.sources.base import FleetVehicle, VehicleSample
from app.traccar.client import TraccarClient
from app.traccar.normalize import apply_positions, roster_from_devices

logger = logging.getLogger(__name__)

# A factory that opens a WebSocket and yields an async stream of text frames.
Frames = AsyncIterator[str | bytes]
Connect = Callable[[], AbstractAsyncContextManager[Frames]]

_RECONNECT_DELAY_S = 3.0


class TraccarStreamSource:
    """Streams live Traccar positions in the background into a snapshot cache."""

    def __init__(
        self,
        client: TraccarClient,
        connect: Connect,
        *,
        reconnect_delay_s: float = _RECONNECT_DELAY_S,
    ) -> None:
        self._client = client
        self._connect = connect
        self._reconnect_delay_s = reconnect_delay_s
        self._roster: dict[str, FleetVehicle] = {}
        self._samples: dict[str, VehicleSample] = {}
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._refresh_roster()
        self._task = asyncio.create_task(self._run())

    def advance(self, dt_seconds: float, now: datetime) -> None:
        """No-op: this source is fed by the background stream, not by ticks."""

    def snapshot(self) -> list[VehicleSample]:
        return list(self._samples.values())

    async def aclose(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self._client.close()

    def _refresh_roster(self) -> None:
        try:
            self._roster = roster_from_devices(self._client.fetch_devices())
        except Exception:  # noqa: BLE001 - a missing roster degrades, not crashes
            logger.warning("failed to load Traccar device roster", exc_info=True)

    async def _run(self) -> None:
        # Reconnect indefinitely; a dropped socket should not end the stream.
        while True:
            try:
                async with self._connect() as frames:
                    await self._consume(frames)
            except Exception:  # noqa: BLE001 - log and retry any connection fault
                logger.warning("Traccar stream error; reconnecting", exc_info=True)
            await asyncio.sleep(self._reconnect_delay_s)

    async def _consume(self, frames: Frames) -> None:
        async for raw in frames:
            self._apply(raw)

    def _apply(self, raw: str | bytes) -> None:
        try:
            frame = json.loads(raw)
        except (ValueError, TypeError):
            logger.debug("dropping unparseable Traccar frame")
            return
        positions = frame.get("positions") if isinstance(frame, dict) else None
        if isinstance(positions, list):
            self._samples = apply_positions(self._roster, self._samples, positions)
