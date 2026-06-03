"""Webhook notifications for CRITICAL anti-theft alerts.

Fires an HTTP POST when a vehicle *enters* a critical state, deduplicated by
(vehicle, alert type) so a persistent condition notifies once rather than on
every broadcast tick. It re-notifies only after the condition clears and recurs.
Disabled (a no-op) when no webhook URL is configured.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import httpx

from app.api.schemas import VehicleOut

logger = logging.getLogger(__name__)

_CRITICAL = "critical"

Sender = Callable[[str, dict[str, Any]], Awaitable[None]]


class CriticalAlertNotifier:
    """Posts newly-active critical alerts to a webhook."""

    def __init__(
        self,
        webhook_url: str,
        *,
        sender: Sender | None = None,
        timeout_s: float = 5.0,
    ) -> None:
        self._url = webhook_url
        self._timeout_s = timeout_s
        self._sender = sender or self._post
        self._active: set[tuple[str, str]] = set()
        self._client: httpx.AsyncClient | None = None

    async def process(self, vehicles: Sequence[VehicleOut]) -> None:
        """Notify for critical alerts that became active since the last call."""
        if not self._url:
            return
        current: set[tuple[str, str]] = set()
        events: dict[tuple[str, str], dict[str, Any]] = {}
        for vehicle in vehicles:
            for alert in vehicle.alerts:
                if alert.severity != _CRITICAL:
                    continue
                key = (vehicle.id, alert.type)
                current.add(key)
                events[key] = {
                    "event": "critical_alert",
                    "vehicle": {
                        "id": vehicle.id,
                        "name": vehicle.name,
                        "plate": vehicle.plate,
                    },
                    "alert": {
                        "type": alert.type,
                        "severity": alert.severity,
                        "reason": alert.reason,
                    },
                    "position": {
                        "lat": vehicle.position.lat,
                        "lon": vehicle.position.lon,
                    },
                    "at": vehicle.position.recorded_at.isoformat(),
                }
        newly_active = current - self._active
        self._active = current
        for key in sorted(newly_active):
            await self._sender(self._url, events[key])

    async def _post(self, url: str, payload: dict[str, Any]) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout_s)
        try:
            await self._client.post(url, json=payload)
        except Exception:  # noqa: BLE001 - a webhook failure must not break the feed
            logger.warning("critical-alert webhook POST failed", exc_info=True)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
