"""Shared fixtures for the Traccar relay tests.

Realistic sample payloads (mirroring Traccar's REST shapes) plus a helper that
wires a :class:`TraccarClient` to an in-memory ``httpx`` transport, so the relay
can be exercised end-to-end without a live server.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
from app.traccar.client import TraccarClient

# A device that is moving with the ignition on; assigned the circular geofence.
DEVICE_VAN: dict[str, Any] = {
    "id": 1,
    "name": "Van 01",
    "uniqueId": "matsue-001",
    "status": "online",
    "positionId": 101,
    "geofenceIds": [10],
}
# A device whose name is blank, so normalization must fall back to uniqueId.
DEVICE_TRUCK: dict[str, Any] = {
    "id": 2,
    "name": "",
    "uniqueId": "yasugi-002",
    "status": "online",
    "positionId": 102,
}
# A device that has never reported a position; it must be dropped.
DEVICE_GHOST: dict[str, Any] = {
    "id": 3,
    "name": "Ghost",
    "uniqueId": "ghost-003",
    "status": "offline",
    "positionId": 0,
}

POSITION_VAN: dict[str, Any] = {
    "id": 101,
    "deviceId": 1,
    "latitude": 35.4723,
    "longitude": 133.0505,
    "speed": 20.0,  # knots
    "course": 90.0,
    "fixTime": "2026-05-29T03:00:00.000+00:00",
    "attributes": {"ignition": True, "motion": True},
}
POSITION_TRUCK: dict[str, Any] = {
    "id": 102,
    "deviceId": 2,
    "latitude": 35.4309,
    "longitude": 133.2503,
    "speed": 0.0,
    "course": 0.0,
    "deviceTime": "2026-05-29T03:00:05Z",
    "attributes": {"ignition": False},
}

DEVICES: list[dict[str, Any]] = [DEVICE_VAN, DEVICE_TRUCK, DEVICE_GHOST]
POSITIONS: list[dict[str, Any]] = [POSITION_VAN, POSITION_TRUCK]

# A circular geofence (Traccar WKT, lat-lon axis order) and a non-circular one
# that normalization must ignore.
GEOFENCE_CIRCLE: dict[str, Any] = {
    "id": 10,
    "name": "Matsue depot",
    "area": "CIRCLE (35.4723 133.0505, 500)",
}
GEOFENCE_POLYGON: dict[str, Any] = {
    "id": 11,
    "name": "Yard",
    "area": "POLYGON ((35.47 133.05, 35.48 133.05, 35.48 133.06, 35.47 133.05))",
}
GEOFENCES: list[dict[str, Any]] = [GEOFENCE_CIRCLE, GEOFENCE_POLYGON]


def build_client(handler: Callable[[httpx.Request], httpx.Response]) -> TraccarClient:
    """Build a TraccarClient backed by an in-memory mock transport."""
    http = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://traccar.test",
        auth=("demo", "secret"),
    )
    return TraccarClient("http://traccar.test", "demo", "secret", client=http)


def static_handler(
    devices: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    geofences: list[dict[str, Any]] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    """A handler that always serves the given devices, positions, geofences."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/devices":
            return httpx.Response(200, json=devices)
        if request.url.path == "/api/positions":
            return httpx.Response(200, json=positions)
        if request.url.path == "/api/geofences":
            return httpx.Response(200, json=geofences or [])
        return httpx.Response(404)

    return handler
