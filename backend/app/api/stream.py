"""WebSocket fan-out that advances the fleet and broadcasts position updates."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from fastapi import WebSocket

from app.api.fleet_service import FleetService

_BROADCAST_INTERVAL_S = 2.0
_STEP_SECONDS = 2.0


class FleetStreamer:
    """Periodically advances the fleet and pushes snapshots to all clients."""

    def __init__(
        self,
        service: FleetService,
        interval_s: float = _BROADCAST_INTERVAL_S,
        step_s: float = _STEP_SECONDS,
    ) -> None:
        self._service = service
        self._interval_s = interval_s
        self._step_s = step_s
        self._clients: set[WebSocket] = set()
        self._task: asyncio.Task[None] | None = None

    def _payload(self) -> dict[str, Any]:
        return {
            "vehicles": [v.model_dump(mode="json") for v in self._service.vehicles()]
        }

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        await websocket.send_json(self._payload())

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    async def _broadcast(self) -> None:
        payload = self._payload()
        for websocket in list(self._clients):
            try:
                await websocket.send_json(payload)
            except Exception:  # noqa: BLE001 - drop any client that errors out
                self.disconnect(websocket)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval_s)
            self._service.advance(self._step_s)
            await self._broadcast()

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
