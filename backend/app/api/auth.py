"""Opt-in user-login session tokens, built with the standard library only.

This is a SECOND authentication gate, independent of the API key. It is
DISABLED unless ``auth_secret`` is set; when empty, the dependency is a no-op
and the keyless mock/quickstart keeps working.

The token is a minimal HS256 JWT (``hmac`` + ``hashlib`` + base64url + ``json``)
so the backend stays dependency-free. ``POST /api/auth/login`` verifies the
configured username/password and issues a signed token carrying ``sub`` and an
``exp`` expiry; the dependency validates the signature and expiry on each
request.

PASSWORD STORAGE:
    ``AUTH_PASSWORD_HASH`` accepts two formats, auto-detected on verify:
    * **scrypt (recommended)** -- a self-describing
      ``scrypt$<n>$<r>$<p>$<salt>$<dk>`` digest from a slow, *salted* KDF
      (:func:`hashlib.scrypt`, standard library -- no extra dependency).
      Generate one with :func:`hash_password`, e.g.::

          python -c "from app.api.auth import hash_password; \
print(hash_password('s3cret'))"

    * **legacy sha256 hex** -- a bare 64-char digest. sha256 is fast and
      *unsalted*, so it is NOT appropriate for production credentials; it is
      kept only for backward compatibility. Prefer the scrypt format.

SECURITY CAVEATS:
    * The signing secret must be high-entropy and kept off the client.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import Cookie, Header, HTTPException, status

_ALG = "HS256"

# Name of the httpOnly cookie the login route sets with the session token, as
# an XSS-resistant alternative to a client-readable store. The dependency and
# the WS guard accept it in addition to a ``Authorization: Bearer`` header.
SESSION_COOKIE_NAME = "fleetguard_session"

# scrypt cost parameters for new digests. n is the CPU/memory cost (a power of
# two); memory use is ~128 * n * r bytes (~16 MiB here), suitable for
# interactive logins. The parameters are stored in each digest so existing
# hashes keep verifying even if these defaults change later.
_SCRYPT_PREFIX = "scrypt$"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
_SCRYPT_MAXMEM = 64 * 1024 * 1024


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


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a self-describing, salted scrypt digest of ``password``.

    Format: ``scrypt$<n>$<r>$<p>$<salt_b64url>$<dk_b64url>``. A fresh 16-byte
    random salt is used unless one is injected (for deterministic tests). This
    is the recommended value for ``AUTH_PASSWORD_HASH``.
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
        maxmem=_SCRYPT_MAXMEM,
    )
    return (
        f"{_SCRYPT_PREFIX}{_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}"
        f"${_b64url_encode(salt)}${_b64url_encode(dk)}"
    )


def _verify_scrypt(stored_hash: str, password: str) -> bool:
    """Constant-time check of ``password`` against a ``scrypt$...`` digest."""
    try:
        _, n_str, r_str, p_str, salt_seg, dk_seg = stored_hash.split("$")
        n, r, p = int(n_str), int(r_str), int(p_str)
        salt = _b64url_decode(salt_seg)
        expected = _b64url_decode(dk_seg)
    except (ValueError, binascii.Error):
        return False
    try:
        computed = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
            maxmem=_SCRYPT_MAXMEM,
        )
    except (ValueError, MemoryError):
        return False
    return hmac.compare_digest(computed, expected)


def verify_password(stored_hash: str, password: str) -> bool:
    """Constant-time check of ``password`` against a stored digest.

    Supports two ``stored_hash`` formats (see the module docstring): a salted
    ``scrypt$...`` digest (recommended) and a legacy bare sha256 hex digest
    (fast and *unsalted* -- backward compatibility only).
    """
    if not stored_hash:
        return False
    if stored_hash.startswith(_SCRYPT_PREFIX):
        return _verify_scrypt(stored_hash, password)
    computed = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(computed, stored_hash.lower())


# A throwaway scrypt digest verified when a username is unknown, so the login
# path does the same slow hashing whether or not the account exists -- denying
# an attacker a timing oracle for username enumeration.
_DUMMY_HASH = hash_password("")


def authenticate(users: Mapping[str, str], username: str, password: str) -> bool:
    """True when ``username`` exists in ``users`` and ``password`` matches.

    Verifies a hash unconditionally -- the stored one when the user exists, a
    dummy otherwise -- so response latency does not reveal whether a username
    is valid. The comparisons inside :func:`verify_password` are constant time.
    """
    stored = users.get(username)
    target = _DUMMY_HASH if stored is None else stored
    matched = verify_password(target, password)
    return matched and stored is not None


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
    The token is read from an ``Authorization: Bearer`` header or, failing that,
    the httpOnly session cookie set by the login route.
    """

    async def dependency(
        authorization: str | None = Header(default=None),
        session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    ) -> None:
        if not secret:
            return
        token = _bearer_token(authorization) or session
        if not token_is_valid(secret, now_fn(), token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing session token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return dependency
