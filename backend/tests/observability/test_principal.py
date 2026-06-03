"""Tests for the per-request authenticated-principal context variable."""

from __future__ import annotations

from app.observability.principal import (
    _principal_var,
    current_principal,
    set_principal,
)


def test_defaults_to_none_outside_a_request() -> None:
    token = _principal_var.set(None)
    try:
        assert current_principal() is None
    finally:
        _principal_var.reset(token)


def test_set_principal_is_readable() -> None:
    token = _principal_var.set(None)
    try:
        set_principal("alice")
        assert current_principal() == "alice"
    finally:
        _principal_var.reset(token)
