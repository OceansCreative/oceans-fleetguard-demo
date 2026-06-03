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
    settings = Settings.from_env()
    assert settings.auth_secret == ""
    assert settings.auth_username == ""
    assert settings.auth_password_hash == ""
    assert settings.auth_token_ttl_s == 3600


def test_auth_env_is_read_and_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_SECRET", "  s3cret  ")
    monkeypatch.setenv("AUTH_USERNAME", " admin ")
    monkeypatch.setenv("AUTH_PASSWORD_HASH", "  ABCDEF  ")
    monkeypatch.setenv("AUTH_TOKEN_TTL_S", "900")
    settings = Settings.from_env()
    assert settings.auth_secret == "s3cret"
    assert settings.auth_username == "admin"
    assert settings.auth_password_hash == "abcdef"
    assert settings.auth_token_ttl_s == 900


def test_token_ttl_falls_back_on_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_TOKEN_TTL_S", "not-a-number")
    assert Settings.from_env().auth_token_ttl_s == 3600
    monkeypatch.setenv("AUTH_TOKEN_TTL_S", "   ")
    assert Settings.from_env().auth_token_ttl_s == 3600
