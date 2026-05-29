"""A :class:`FleetSource` backed by a live Traccar server.

Each :meth:`advance` polls Traccar once and caches the result; :meth:`snapshot`
returns that cache, carrying each vehicle's prior position forward so the
detection engine can reason about movement between polls. A failed poll keeps
the last good snapshot rather than blanking the dashboard.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from app.sources.base import VehicleSample
from app.traccar.client import TraccarClient
from app.traccar.normalize import geofences_by_id, merge_readings

logger = logging.getLogger(__name__)


class TraccarSource:
    """Relays normalized Traccar data, tracking previous positions across polls."""

    def __init__(self, client: TraccarClient) -> None:
        self._client = client
        self._samples: dict[str, VehicleSample] = {}
        self._polled = False

    async def start(self) -> None:
        """No-op; the first poll happens lazily on the first read or tick."""

    def advance(self, dt_seconds: float, now: datetime) -> None:
        """Poll Traccar for fresh data. ``dt_seconds``/``now`` are unused here."""
        self._poll()

    def snapshot(self) -> list[VehicleSample]:
        # Lazily poll on first read so REST callers get data before the streamer
        # has had a chance to tick.
        if not self._polled:
            self._poll()
        return list(self._samples.values())

    async def aclose(self) -> None:
        self._client.close()

    def _poll(self) -> None:
        try:
            devices = self._client.fetch_devices()
            positions = self._client.fetch_positions()
            geofences = geofences_by_id(self._client.fetch_geofences())
        except (httpx.HTTPError, ValueError):
            logger.warning(
                "Traccar poll failed; serving last known snapshot", exc_info=True
            )
            self._polled = True
            return

        updated: dict[str, VehicleSample] = {}
        for reading in merge_readings(devices, positions, geofences):
            previous = self._samples.get(reading.vehicle.id)
            updated[reading.vehicle.id] = VehicleSample(
                vehicle=reading.vehicle,
                current=reading.position,
                previous=previous.current if previous is not None else None,
            )
        self._samples = updated
        self._polled = True
