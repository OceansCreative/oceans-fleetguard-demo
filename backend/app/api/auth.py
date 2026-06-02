"""Opt-in user-login session tokens, built with the standard library only.

This is a SECOND authentication gate, independent of the API key. It is
DISABLED unless ``auth_secret`` is set; when empty, the dependency is a no-op
and the keyless mock/quickstart keeps working.

The token is a minimal HS256 JWT (``hmac`` + ``hashlib`` + base64url + ``json``)
so the backend stays dependency-free. ``POST /api/auth/login`` verifies the
configured username/password and issues a signed token carrying ``sub`` and an
``exp`` expiry; the dependency validates the signature and expiry on each
request.

SECURITY CAVEATS:
    * Passwords are checked against a *plain sha256 hex* digest. sha256 is fast
      and unsalted, so it is unsuitable for production credential storage — use
      a slow, salted KDF (bcrypt/argon2/scrypt). That is intentionally out of
      scope here to avoid adding a dependency for this MVP.
    * The signing secret must be high-entropy and kept off the client.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Header, HTTPException, status

_ALG = "HS256"


def _b64url_encode(raw: bytes) -> str:
    """URL-safe base64 without padding (per the JWT spec)."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    """Decode URL-safe base64, restoring the stripped ``=`` padding."""
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _sign(secret: str, signing_input: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return _b64url_encode(digest)


def issue_token(secret: str, sub: str, now: int, ttl_s: int) -> str:
    """Issue a signed HS256 token for ``sub`` valid for ``ttl_s`` seconds.

    Args:
        secret: HMAC signing secret.
        sub: Subject (the authenticated username).
        now: Current Unix time in seconds (injected for testability).
        ttl_s: Lifetime in seconds; ``exp`` is ``now + ttl_s``.
    """
    header = {"alg": _ALG, "typ": "JWT"}
    payload = {"sub": sub, "iat": now, "exp": now + ttl_s}
    header_seg = _b64url_encode(_compact_json(header))
    payload_seg = _b64url_encode(_compact_json(payload))
    signing_input = f"{header_seg}.{payload_seg}".encode("ascii")
    signature = _sign(secret, signing_input)
    return f"{header_seg}.{payload_seg}.{signature}"


def _compact_json(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def verify_token(secret: str, token: str, now: int) -> dict[str, Any] | None:
    """Verify signature and expiry; return the claims, or ``None`` if invalid.

    The signature is compared with :func:`hmac.compare_digest` to avoid leaking
    timing information. A token whose ``exp`` is at or before ``now`` is
    rejected.
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_seg, payload_seg, signature = parts
    signing_input = f"{header_seg}.{payload_seg}".encode("ascii")
    expected = _sign(secret, signing_input)
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        claims = json.loads(_b64url_decode(payload_seg))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(claims, dict):
        return None
    exp = claims.get("exp")
    if not isinstance(exp, int) or now >= exp:
        return None
    return claims


def verify_password(stored_hash: str, password: str) -> bool:
    """Constant-time check of ``password`` against a sha256 hex digest.

    NOTE: sha256 is a *fast, unsalted* hash and is NOT appropriate for storing
    credentials in production — prefer a slow, salted KDF such as bcrypt or
    argon2. It is used here only to keep this MVP dependency-free.
    """
    if not stored_hash:
        return False
    computed = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(computed, stored_hash.lower())


def _bearer_token(authorization: str | None) -> str | None:
    """Extract a bearer token from an ``Authorization`` header value."""
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token
    return None


def token_is_valid(secret: str, now: int, token: str | None) -> bool:
    """True when auth is disabled (no secret) or ``token`` verifies."""
    if not secret:
        return True
    if token is None:
        return False
    return verify_token(secret, token, now) is not None


def make_auth_dependency(
    secret: str, now_fn: Callable[[], int]
) -> Callable[..., Awaitable[None]]:
    """Build a FastAPI dependency enforcing a valid session token.

    When ``secret`` is empty the dependency is a no-op, leaving routes open.
    ``now_fn`` supplies the current Unix time, injected so tests need no sleeps.
    """

    async def dependency(authorization: str | None = Header(default=None)) -> None:
        if not secret:
            return
        token = _bearer_token(authorization)
        if not token_is_valid(secret, now_fn(), token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing session token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return dependency
