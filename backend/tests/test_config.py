"""Tests for environment-driven settings, focused on the auth additions."""

from __future__ import annotations

import pytest
from app.config import Settings


def test_auth_defaults_to_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "AUTH_SECRET",
        "AUTH_USERNAME",
        "AUTH_PASSWORD_HASH",
        "AUTH_TOKEN_TTL_S",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("AUTH_USERS", raising=False)
    settings = Settings.from_env()
    assert settings.auth_secret == ""
    assert settings.auth_username == ""
    assert settings.auth_password_hash == ""
    assert settings.auth_token_ttl_s == 3600
    assert settings.auth_users == ()
    assert settings.credential_store() == {}


def test_auth_users_json_is_parsed_and_merged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_USERS", '{"alice": "hash-a", "bob": "hash-b"}')
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("AUTH_PASSWORD_HASH", "hash-admin")
    settings = Settings.from_env()
    # Stored sorted as pairs, and merged with the single-user shorthand.
    assert settings.auth_users == (("alice", "hash-a"), ("bob", "hash-b"))
    assert settings.credential_store() == {
        "alice": "hash-a",
        "bob": "hash-b",
        "admin": "hash-admin",
    }


def test_auth_users_ignores_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTH_USERNAME", raising=False)
    monkeypatch.delenv("AUTH_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("AUTH_USERS", "not-json")
    assert Settings.from_env().auth_users == ()
    # Valid JSON that isn't an object is ignored too.
    monkeypatch.setenv("AUTH_USERS", '["alice", "bob"]')
    assert Settings.from_env().auth_users == ()


def test_explicit_user_wins_over_single_user_shorthand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_USERS", '{"admin": "from-store"}')
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("AUTH_PASSWORD_HASH", "from-shorthand")
    assert Settings.from_env().credential_store() == {"admin": "from-store"}


def test_auth_env_is_read_and_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_SECRET", "  s3cret  ")
    monkeypatch.setenv("AUTH_USERNAME", " admin ")
    # The hash is stripped but case-preserved: a scrypt digest carries
    # case-sensitive base64; the legacy hex path lowercases at verify time.
    monkeypatch.setenv("AUTH_PASSWORD_HASH", "  scrypt$16384$8$1$AbC$dEf  ")
    monkeypatch.setenv("AUTH_TOKEN_TTL_S", "900")
    settings = Settings.from_env()
    assert settings.auth_secret == "s3cret"
    assert settings.auth_username == "admin"
    assert settings.auth_password_hash == "scrypt$16384$8$1$AbC$dEf"
    assert settings.auth_token_ttl_s == 900


def test_token_ttl_falls_back_on_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_TOKEN_TTL_S", "not-a-number")
    assert Settings.from_env().auth_token_ttl_s == 3600
    monkeypatch.setenv("AUTH_TOKEN_TTL_S", "   ")
    assert Settings.from_env().auth_token_ttl_s == 3600
