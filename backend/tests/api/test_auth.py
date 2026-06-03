"""Tests for the opt-in user-login session-token gate."""

from __future__ import annotations

import asyncio
import hashlib

import pytest
from app.api.auth import (
    hash_password,
    issue_token,
    make_auth_dependency,
    token_is_valid,
    verify_password,
    verify_token,
)
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

_SECRET = "signing-secret"
_PASSWORD = "hunter2"
_PW_HASH = hashlib.sha256(_PASSWORD.encode()).hexdigest()


def _settings(*, auth: bool = False, api_key: str = "", ttl_s: int = 3600) -> Settings:
    return Settings(
        mock_mode=True,
        cors_origins=("http://localhost:3000",),
        traccar_base_url="http://traccar:8082",
        traccar_ws_url="ws://traccar:8082/api/socket",
        traccar_username="",
        traccar_password="",
        traccar_transport="ws",
        api_key=api_key,
        auth_secret=_SECRET if auth else "",
        auth_username="admin" if auth else "",
        auth_password_hash=_PW_HASH if auth else "",
        auth_token_ttl_s=ttl_s,
    )


def _client(**kwargs: object) -> TestClient:
    return TestClient(create_app(_settings(**kwargs)))  # type: ignore[arg-type]


# --- token issue / verify -------------------------------------------------


def test_issue_then_verify_roundtrips_claims() -> None:
    token = issue_token(_SECRET, "admin", now=1000, ttl_s=60)
    claims = verify_token(_SECRET, token, now=1000)
    assert claims is not None
    assert claims["sub"] == "admin"
    assert claims["exp"] == 1060


def test_expired_token_is_rejected() -> None:
    token = issue_token(_SECRET, "admin", now=1000, ttl_s=60)
    assert verify_token(_SECRET, token, now=1060) is None
    assert verify_token(_SECRET, token, now=2000) is None


def test_tampered_signature_is_rejected() -> None:
    token = issue_token(_SECRET, "admin", now=1000, ttl_s=60)
    head, payload, _sig = token.split(".")
    forged = f"{head}.{payload}.AAAAtampered"
    assert verify_token(_SECRET, forged, now=1000) is None


def test_wrong_secret_is_rejected() -> None:
    token = issue_token(_SECRET, "admin", now=1000, ttl_s=60)
    assert verify_token("other-secret", token, now=1000) is None


def test_malformed_token_is_rejected() -> None:
    assert verify_token(_SECRET, "not-a-jwt", now=0) is None
    assert verify_token(_SECRET, "a.b", now=0) is None


def test_token_with_corrupt_payload_is_rejected() -> None:
    from app.api.auth import _b64url_encode, _sign

    head = _b64url_encode(b'{"alg":"HS256"}')
    payload = _b64url_encode(b"not json")
    sig = _sign(_SECRET, f"{head}.{payload}".encode("ascii"))
    assert verify_token(_SECRET, f"{head}.{payload}.{sig}", now=0) is None


def test_token_with_non_dict_claims_is_rejected() -> None:
    from app.api.auth import _b64url_encode, _sign

    head = _b64url_encode(b'{"alg":"HS256"}')
    payload = _b64url_encode(b"[1, 2, 3]")
    sig = _sign(_SECRET, f"{head}.{payload}".encode("ascii"))
    assert verify_token(_SECRET, f"{head}.{payload}.{sig}", now=0) is None


def test_token_without_exp_is_rejected() -> None:
    from app.api.auth import _b64url_encode, _sign

    head = _b64url_encode(b'{"alg":"HS256"}')
    payload = _b64url_encode(b'{"sub":"admin"}')
    sig = _sign(_SECRET, f"{head}.{payload}".encode("ascii"))
    assert verify_token(_SECRET, f"{head}.{payload}.{sig}", now=0) is None


def test_token_is_valid_passthrough_when_disabled() -> None:
    assert token_is_valid("", now=0, token=None) is True


def test_token_is_valid_requires_token_when_enabled() -> None:
    assert token_is_valid(_SECRET, now=0, token=None) is False


# --- password verification ------------------------------------------------


def test_verify_password_accepts_matching_hash() -> None:
    assert verify_password(_PW_HASH, _PASSWORD) is True


def test_verify_password_rejects_wrong_password() -> None:
    assert verify_password(_PW_HASH, "wrong") is False


def test_verify_password_rejects_empty_hash() -> None:
    assert verify_password("", _PASSWORD) is False


def test_hash_password_roundtrips_with_scrypt() -> None:
    digest = hash_password(_PASSWORD)
    assert digest.startswith("scrypt$")
    assert verify_password(digest, _PASSWORD) is True
    assert verify_password(digest, "wrong") is False


def test_hash_password_uses_a_random_salt() -> None:
    # Two hashes of the same password differ (distinct random salts), but both
    # verify -- the property a salted KDF must have.
    first = hash_password(_PASSWORD)
    second = hash_password(_PASSWORD)
    assert first != second
    assert verify_password(first, _PASSWORD) is True
    assert verify_password(second, _PASSWORD) is True


def test_hash_password_accepts_injected_salt_for_determinism() -> None:
    salt = b"sixteen-byte-salt"[:16]
    assert hash_password(_PASSWORD, salt=salt) == hash_password(_PASSWORD, salt=salt)


def test_verify_password_rejects_malformed_scrypt_digest() -> None:
    assert verify_password("scrypt$not$enough$fields", _PASSWORD) is False
    assert verify_password("scrypt$16384$8$1$@@@$@@@", _PASSWORD) is False


# --- login route ----------------------------------------------------------


def test_login_succeeds_and_returns_a_usable_token() -> None:
    client = _client(auth=True)
    resp = client.post(
        "/api/auth/login", json={"username": "admin", "password": _PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert isinstance(body["expires_at"], int)
    # The issued token unlocks the gated API.
    ok = client.get(
        "/api/vehicles", headers={"Authorization": f"Bearer {body['token']}"}
    )
    assert ok.status_code == 200


def test_login_rejects_a_bad_password() -> None:
    resp = _client(auth=True).post(
        "/api/auth/login", json={"username": "admin", "password": "nope"}
    )
    assert resp.status_code == 401


def test_login_rejects_an_unknown_username() -> None:
    resp = _client(auth=True).post(
        "/api/auth/login", json={"username": "ghost", "password": _PASSWORD}
    )
    assert resp.status_code == 401


def test_login_is_disabled_when_no_secret_is_set() -> None:
    resp = _client(auth=False).post(
        "/api/auth/login", json={"username": "admin", "password": _PASSWORD}
    )
    assert resp.status_code == 401


# --- REST dependency ------------------------------------------------------


def test_rest_is_open_when_auth_is_disabled() -> None:
    assert _client(auth=False).get("/api/vehicles").status_code == 200


def test_rest_rejects_a_missing_token_when_auth_is_enabled() -> None:
    assert _client(auth=True).get("/api/vehicles").status_code == 401


def test_rest_rejects_an_invalid_token() -> None:
    resp = _client(auth=True).get(
        "/api/vehicles", headers={"Authorization": "Bearer garbage"}
    )
    assert resp.status_code == 401


# --- WebSocket ------------------------------------------------------------


def test_ws_is_open_when_auth_is_disabled() -> None:
    with (
        _client(auth=False) as client,
        client.websocket_connect("/ws/positions") as ws,
    ):
        assert "vehicles" in ws.receive_json()


def test_ws_accepts_a_valid_token_query_parameter() -> None:
    client = _client(auth=True)
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": _PASSWORD}
    ).json()["token"]
    with client as c, c.websocket_connect(f"/ws/positions?token={token}") as ws:
        assert "vehicles" in ws.receive_json()


def test_ws_rejects_a_missing_token_when_auth_is_enabled() -> None:
    with _client(auth=True) as client:  # noqa: SIM117
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/positions") as ws:
                ws.receive_json()


# --- dependency unit (no app) ---------------------------------------------


async def _run_dep(secret: str, authorization: str | None) -> None:
    dep = make_auth_dependency(secret, lambda: 0)
    await dep(authorization=authorization)


def test_make_auth_dependency_is_noop_when_disabled() -> None:
    assert asyncio.run(_run_dep("", None)) is None


def test_make_auth_dependency_raises_on_bad_token() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        asyncio.run(_run_dep(_SECRET, "Bearer nope"))
    assert exc.value.status_code == 401


def test_make_auth_dependency_rejects_non_bearer_scheme() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        asyncio.run(_run_dep(_SECRET, "Basic abc"))
