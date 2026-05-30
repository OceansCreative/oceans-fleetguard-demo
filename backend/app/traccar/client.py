"""A thin synchronous HTTP client for the Traccar REST API.

This wrapper deliberately does almost nothing beyond issuing two authenticated
GETs and returning parsed JSON; all interpretation happens in
:mod:`app.traccar.normalize`. An ``httpx.Client`` can be injected so tests can
drive it with a mock transport instead of a live server.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S = 10.0


class TraccarClient:
    """Fetches the device roster and latest positions from Traccar."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
        client: httpx.Client | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            auth=(username, password),
            timeout=timeout_s,
        )

    def session_cookie(self) -> str:
        """Authenticate and return the session cookie for the WebSocket feed.

        Traccar's ``/api/socket`` only accepts a logged-in session, so we POST
        the credentials to ``/api/session`` (which sets ``JSESSIONID``) and hand
        the cookie back as a ``Cookie`` header value. The account name is sent as
        Traccar's ``email`` field.
        """
        response = self._client.post(
            "/api/session",
            data={"email": self._username, "password": self._password},
        )
        response.raise_for_status()
        session_id = self._client.cookies.get("JSESSIONID")
        if not session_id:
            # A 2xx with no JSESSIONID almost always means bad credentials.
            # Surface it: otherwise the stream silently reconnects forever with
            # an empty cookie, getting 401s, with nothing pointing at the cause.
            logger.warning(
                "Traccar login succeeded but set no JSESSIONID cookie; "
                "check TRACCAR_USERNAME/TRACCAR_PASSWORD"
            )
            return ""
        return f"JSESSIONID={session_id}"

    def fetch_devices(self) -> list[dict[str, Any]]:
        """Return all devices known to Traccar (``GET /api/devices``)."""
        return self._get_json("/api/devices")

    def fetch_positions(self) -> list[dict[str, Any]]:
        """Return the latest position per device (``GET /api/positions``)."""
        return self._get_json("/api/positions")

    def fetch_geofences(self) -> list[dict[str, Any]]:
        """Return all geofences known to Traccar (``GET /api/geofences``)."""
        return self._get_json("/api/geofences")

    def _get_json(self, path: str) -> list[dict[str, Any]]:
        response = self._client.get(path)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError(f"expected a JSON array from {path}")
        return payload

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()
