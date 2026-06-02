"""Tests for the request-ID middleware."""

from __future__ import annotations

import re

from app.observability.middleware import _HEADER, RequestIDMiddleware
from app.observability.request_id import (
    current_request_id,
    generate_request_id,
    set_request_id,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/echo-rid")
    def echo() -> dict[str, str | None]:
        return {"request_id": current_request_id()}

    return app


_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class TestRequestIDMiddleware:
    def test_echoes_provided_request_id(self) -> None:
        client = TestClient(_make_app())
        resp = client.get("/echo-rid", headers={_HEADER: "my-rid-123"})
        assert resp.headers[_HEADER] == "my-rid-123"

    def test_generates_uuid4_when_header_absent(self) -> None:
        client = TestClient(_make_app())
        resp = client.get("/echo-rid")
        rid = resp.headers.get(_HEADER)
        assert rid is not None
        assert _UUID4_RE.match(rid), f"Not a UUID-4: {rid!r}"

    def test_request_id_available_inside_handler(self) -> None:
        client = TestClient(_make_app())
        resp = client.get("/echo-rid", headers={_HEADER: "handler-check"})
        assert resp.json()["request_id"] == "handler-check"

    def test_different_requests_get_different_ids(self) -> None:
        client = TestClient(_make_app())
        rid1 = client.get("/echo-rid").headers[_HEADER]
        rid2 = client.get("/echo-rid").headers[_HEADER]
        assert rid1 != rid2


class TestRequestIdHelpers:
    def test_generate_request_id_returns_uuid4(self) -> None:
        rid = generate_request_id()
        assert _UUID4_RE.match(rid), f"Not a UUID-4: {rid!r}"

    def test_set_and_get_request_id(self) -> None:
        from app.observability.request_id import _request_id_var

        token = _request_id_var.set(None)
        try:
            assert current_request_id() is None
            set_request_id("test-id")
            assert current_request_id() == "test-id"
        finally:
            _request_id_var.reset(token)
