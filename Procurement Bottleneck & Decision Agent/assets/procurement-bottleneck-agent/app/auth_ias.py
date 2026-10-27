"""IAS (SAP Cloud Identity Services) inbound token validation — L0-5 / principal propagation.

When the agent is invoked by Joule over A2A, Joule delivers an **IAS** user token
(not XSUAA — Joule no longer uses XSUAA). This module validates that token at the
A2A boundary: fetch IAS's JWKS, verify the RS256 signature, issuer, expiry, and the
audience/API grant. It mirrors the proven `IASAuthMiddleware` pattern from the SAP
"Joule A2A: Secure Code Based Agents with IAS" blog.

Selected by ``AGENT_AUTH_MODE=ias`` (see config). Kept framework-light and with the
JWKS fetch isolated behind ``_fetch_jwks`` so it is unit-testable offline with a
generated key pair.

Audience note (deliberate flexibility): the IAS token observed in the blog carries
the agent's API grant in the ``ias_apis`` claim and may leave ``aud`` empty, while
other sources describe ``aud`` = the agent app's client id. The exact semantics are
environment-dependent, so we accept the token if EITHER the configured required API
is present in ``ias_apis`` OR ``aud`` equals the configured audience. Signature,
issuer, and expiry are always enforced.
"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

_JWKS_CACHE: dict[str, tuple[float, dict]] = {}
_JWKS_TTL_SECONDS = 3600


class IASValidationError(Exception):
    """Raised when an inbound IAS token cannot be validated."""


def _fetch_jwks(jwks_uri: str) -> dict:
    """Fetch (and cache) the IAS JWKS. Isolated so tests can patch it."""
    now = time.time()
    cached = _JWKS_CACHE.get(jwks_uri)
    if cached and now - cached[0] < _JWKS_TTL_SECONDS:
        return cached[1]
    resp = httpx.get(jwks_uri, timeout=10)
    resp.raise_for_status()
    jwks = resp.json()
    _JWKS_CACHE[jwks_uri] = (now, jwks)
    return jwks


def reset_jwks_cache() -> None:
    _JWKS_CACHE.clear()


def _signing_key(token: str, jwks: dict) -> Any:
    import jwt  # PyJWT[crypto]

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    keys = jwks.get("keys", [])
    for key in keys:
        if kid is None or key.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    raise IASValidationError("No matching JWKS key for the token's 'kid'.")


def validate_ias_token(
    token: str,
    *,
    issuer: str,
    audience: str | None = None,
    jwks_uri: str,
    required_api: str | None = None,
) -> dict[str, Any]:
    """Validate an IAS JWT and return its claims.

    Always enforces: RS256 signature against the JWKS, matching ``iss``, and ``exp``.
    Audience is accepted if ``required_api`` is in the ``ias_apis`` claim OR ``aud``
    equals ``audience`` (whichever is configured). Raises ``IASValidationError``.
    """
    try:
        import jwt  # PyJWT[crypto]
    except ImportError as exc:  # pragma: no cover - runtime provides it
        raise IASValidationError(
            "PyJWT[crypto] unavailable; refusing the request rather than trusting it."
        ) from exc

    if not issuer:
        raise IASValidationError("IAS_ISSUER is not configured.")
    if not jwks_uri:
        raise IASValidationError("IAS_JWKS_URI is not configured.")

    jwks = _fetch_jwks(jwks_uri)
    key = _signing_key(token, jwks)
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"require": ["exp"], "verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise IASValidationError(f"IAS token validation failed: {exc}") from exc

    ias_apis = claims.get("ias_apis") or []
    aud = claims.get("aud")
    aud_values = aud if isinstance(aud, list) else [aud]
    audience_ok = (
        (required_api is not None and required_api in ias_apis)
        or (audience is not None and audience in aud_values)
        or (required_api is None and audience is None)  # nothing to check against
    )
    if not audience_ok:
        raise IASValidationError(
            "Token audience/API grant does not match this agent "
            f"(ias_apis={ias_apis!r}, aud={aud!r})."
        )
    return claims


def decode_unverified(token: str) -> dict[str, Any]:
    """Decode a JWT WITHOUT signature verification — for /whoami diagnostics only.

    Never use for authorization. Returns a small, non-sensitive claim subset so the
    operator can see which identity arrived at the agent without exposing the token.
    """
    try:
        import jwt  # PyJWT[crypto]
        claims = jwt.decode(token, options={"verify_signature": False})
    except Exception as exc:  # malformed / lib missing
        return {"error": f"could not decode token: {exc}"}
    return {k: claims.get(k) for k in ("sub", "mail", "email", "aud", "iss", "ias_apis", "azp", "exp")
            if k in claims}
