"""Tests for the AUTH_USERS generator CLI."""

from __future__ import annotations

import json

import pytest
from app.tools.gen_auth_users import (
    build_auth_users,
    main,
    render_env,
    split_pair,
)


def _fake_hash(password: str) -> str:
    """Deterministic stand-in for scrypt hashing in tests."""
    return f"hash({password})"


class TestSplitPair:
    def test_inline_password_is_returned(self) -> None:
        assert split_pair("alice:s3cret") == ("alice", "s3cret")

    def test_username_is_stripped(self) -> None:
        assert split_pair("  alice  :pw") == ("alice", "pw")

    def test_missing_password_yields_none(self) -> None:
        assert split_pair("alice") == ("alice", None)

    def test_empty_inline_password_is_kept(self) -> None:
        # A trailing colon means "empty password", not "prompt me".
        assert split_pair("alice:") == ("alice", "")

    def test_missing_username_raises(self) -> None:
        with pytest.raises(ValueError):
            split_pair(":pw")


class TestBuildAuthUsers:
    def test_hashes_each_password(self) -> None:
        users = build_auth_users(
            [("alice", "a-pw"), ("bob", "b-pw")], hasher=_fake_hash
        )
        assert users == {"alice": "hash(a-pw)", "bob": "hash(b-pw)"}

    def test_duplicate_username_raises(self) -> None:
        with pytest.raises(ValueError):
            build_auth_users([("alice", "x"), ("alice", "y")], hasher=_fake_hash)


def test_render_env_is_compact_and_sorted() -> None:
    line = render_env({"bob": "hb", "alice": "ha"})
    assert line == 'AUTH_USERS={"alice":"ha","bob":"hb"}'
    # The value parses back to the same mapping.
    assert json.loads(line.removeprefix("AUTH_USERS=")) == {"alice": "ha", "bob": "hb"}


class TestMain:
    def test_inline_passwords_print_env_line(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(["alice:a-pw", "bob:b-pw"], hasher=_fake_hash)
        assert code == 0
        out = capsys.readouterr().out.strip()
        assert out == 'AUTH_USERS={"alice":"hash(a-pw)","bob":"hash(b-pw)"}'

    def test_missing_password_is_prompted(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        prompts: list[str] = []

        def fake_prompt(message: str) -> str:
            prompts.append(message)
            return "prompted-pw"

        code = main(["alice"], prompt=fake_prompt, hasher=_fake_hash)
        assert code == 0
        assert prompts == ["Password for alice: "]
        out = capsys.readouterr().out.strip()
        assert out == 'AUTH_USERS={"alice":"hash(prompted-pw)"}'

    def test_invalid_input_returns_error_code(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main([":no-user"], hasher=_fake_hash)
        assert code == 2
        assert "error" in capsys.readouterr().err
