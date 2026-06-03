"""Tests for the thin Traccar HTTP client (driven by a mock transport)."""

from __future__ import annotations

import base64

import httpx
import pytest

from tests.traccar._helpers import (
    DEVICES,
    GEOFENCES,
    POSITIONS,
    build_client,
    static_handler,
)


def test_fetch_devices_and_positions_return_parsed_json() -> None:
    client = build_client(static_handler(DEVICES, POSITIONS))
    assert client.fetch_devices() == DEVICES
    assert client.fetch_positions() == POSITIONS
    client.close()


def test_requests_carry_basic_auth_and_hit_the_expected_paths() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen[request.url.path] = request.headers.get("authorization", "")
        return httpx.Response(200, json=[])

    client = build_client(handler)
    client.fetch_devices()
    client.fetch_positions()

    expected = "Basic " + base64.b64encode(b"demo:secret").decode()
    assert seen["/api/devices"] == expected
    assert seen["/api/positions"] == expected


def test_http_errors_propagate() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    client = build_client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.fetch_devices()


def test_non_array_payload_is_rejected() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"not": "a list"})

    client = build_client(handler)
    with pytest.raises(ValueError):
        client.fetch_devices()


def test_session_cookie_posts_credentials_and_returns_jsessionid() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/session":
            captured["body"] = request.content.decode()
            return httpx.Response(
                200,
                headers={"Set-Cookie": "JSESSIONID=abc123; Path=/"},
                json={"id": 1},
            )
        return httpx.Response(404)

    client = build_client(handler)
    cookie = client.session_cookie()

    assert cookie == "JSESSIONID=abc123"
    assert "email=demo" in captured["body"]
    assert "password=secret" in captured["body"]


def test_session_cookie_is_empty_and_warns_when_no_cookie_is_set(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": 1})

    with caplog.at_level("WARNING"):
        assert build_client(handler).session_cookie() == ""

    # The misconfiguration must be visible, not swallowed into a silent retry.
    assert any("JSESSIONID" in record.message for record in caplog.records)


def test_fetch_geofences_returns_parsed_json() -> None:
    client = build_client(static_handler([], [], GEOFENCES))
    assert client.fetch_geofences() == GEOFENCES
    client.close()
