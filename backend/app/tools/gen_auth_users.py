"""CLI: build an ``AUTH_USERS`` value from username/password pairs.

Hashes each password with the same salted scrypt KDF the login route verifies
(:func:`app.api.auth.hash_password`) and prints a ready-to-paste env line::

    $ python -m app.tools.gen_auth_users alice:s3cret bob
    Password for bob: ...
    AUTH_USERS={"alice":"scrypt$...","bob":"scrypt$..."}

Pass ``username:password`` inline, or just ``username`` to be prompted (the
prompt is preferred -- inline passwords land in your shell history). The pure
helpers below are unit-tested with injected fakes; ``main`` is the thin shell.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from collections.abc import Callable, Sequence

from app.api.auth import hash_password


def split_pair(raw: str) -> tuple[str, str | None]:
    """Split ``username[:password]``; the password is ``None`` when omitted."""
    username, sep, password = raw.partition(":")
    username = username.strip()
    if not username:
        raise ValueError(f"missing username in {raw!r}")
    return username, (password if sep else None)


def build_auth_users(
    pairs: Sequence[tuple[str, str]],
    *,
    hasher: Callable[[str], str] = hash_password,
) -> dict[str, str]:
    """Hash each ``(username, password)`` into an ``AUTH_USERS`` mapping."""
    users: dict[str, str] = {}
    for username, password in pairs:
        if username in users:
            raise ValueError(f"duplicate username {username!r}")
        users[username] = hasher(password)
    return users


def render_env(users: dict[str, str]) -> str:
    """Render the ``AUTH_USERS=<json>`` line (compact, sorted keys)."""
    payload = json.dumps(users, separators=(",", ":"), sort_keys=True)
    return f"AUTH_USERS={payload}"


def _resolve_password(
    username: str, password: str | None, prompt: Callable[[str], str]
) -> str:
    if password is not None:
        return password
    return prompt(f"Password for {username}: ")


def main(
    argv: Sequence[str] | None = None,
    *,
    prompt: Callable[[str], str] = getpass.getpass,
    hasher: Callable[[str], str] = hash_password,
) -> int:
    """Parse args, hash passwords, and print the ``AUTH_USERS`` line."""
    parser = argparse.ArgumentParser(
        prog="python -m app.tools.gen_auth_users",
        description="Build an AUTH_USERS value from username/password pairs.",
    )
    parser.add_argument(
        "users",
        nargs="+",
        metavar="USERNAME[:PASSWORD]",
        help="A username, optionally with an inline password (prompted if omitted).",
    )
    args = parser.parse_args(argv)
    try:
        pairs = [
            (username, _resolve_password(username, password, prompt))
            for username, password in (split_pair(raw) for raw in args.users)
        ]
        users = build_auth_users(pairs, hasher=hasher)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(render_env(users))
    return 0


if __name__ == "__main__":  # pragma: no cover - thin CLI entrypoint
    raise SystemExit(main())
