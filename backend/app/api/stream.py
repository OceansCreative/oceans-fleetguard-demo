"""WebSocket fan-out that advances the fleet and broadcasts position updates."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from fastapi import WebSocket

from app.alerts.history import AlertHistory
from app.api.fleet_service import FleetService
from app.notify.webhook import CriticalAlertNotifier

logger = logging.getLogger(__name__)

_BROADCAST_INTERVAL_S = 2.0
_STEP_SECONDS = 2.0


class FleetStreamer:
    """Periodically advances the fleet and pushes snapshots to all clients."""

    def __init__(
        self,
        service: FleetService,
        interval_s: float = _BROADCAST_INTERVAL_S,
        step_s: float = _STEP_SECONDS,
        notifier: CriticalAlertNotifier | None = None,
        history: AlertHistory | None = None,
    ) -> None:
        self._service = service
        self._interval_s = interval_s
        self._step_s = step_s
        self._clients: set[WebSocket] = set()
        self._task: asyncio.Task[None] | None = None
        # Disabled no-op notifier unless one is injected.
        self._notifier = notifier or CriticalAlertNotifier("")
        self._history = history

    def _payload(self) -> dict[str, Any]:
        return {
            "vehicles": [v.model_dump(mode="json") for v in self._service.vehicles()]
        }

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        # Building the first snapshot can poll Traccar (REST transport); run it
        # off the event loop so one connecting client can't stall the server.
        payload = await asyncio.to_thread(self._payload)
        await websocket.send_json(payload)

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    async def _broadcast(self, payload: dict[str, Any] | None = None) -> None:
        data = payload if payload is not None else self._payload()
        for websocket in list(self._clients):
            try:
                await websocket.send_json(data)
            except Exception:  # noqa: BLE001 - drop any client that errors out
                self.disconnect(websocket)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval_s)
            try:
                # ``advance`` may poll Traccar over the network (REST transport);
                # keep it off the event loop so a slow upstream can't freeze
                # every client's feed and ``/health``.
                await asyncio.to_thread(self._service.advance, self._step_s)
                vehicles = self._service.vehicles()
                tick_payload: dict[str, Any] = {
                    "vehicles": [v.model_dump(mode="json") for v in vehicles]
                }
                await self._broadcast(tick_payload)
                await self._notifier.process(vehicles)
                if self._history is not None:
                    self._history.record(vehicles)
            except Exception:  # noqa: BLE001 - one bad tick must not end the stream
                logger.warning("fleet broadcast tick failed; skipping", exc_info=True)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._notifier.aclose()
