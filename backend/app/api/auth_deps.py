"""
Supabase JWT authentication dependencies for FastAPI.

Supabase uses ES256 (ECC P-256) for signing user access tokens.
We verify tokens locally by fetching the JWKS once and caching them
for one hour — no round-trip per request.

Usage
-----
    from app.api.auth_deps import get_current_user, get_optional_user

    @router.get("/items")
    async def list_items(user=Depends(get_current_user)):
        ...  # user.sub is the Supabase user UUID
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt  # python-jose[cryptography]

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── JWKS cache ────────────────────────────────────────────────────────────────

_JWKS_CACHE: dict[str, Any] = {}         # {"keys": [...], "fetched_at": float}
_JWKS_TTL = 3600                          # re-fetch every hour

bearer_scheme = HTTPBearer(auto_error=False)


async def _get_jwks() -> list[dict]:
    """Return cached JWKS keys, re-fetching when stale."""
    now = time.time()
    if _JWKS_CACHE and now - _JWKS_CACHE.get("fetched_at", 0) < _JWKS_TTL:
        return _JWKS_CACHE["keys"]

    settings = get_settings()
    if not settings.supabase_url:
        logger.warning("SUPABASE_URL not configured — JWT verification disabled")
        return []

    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            data = resp.json()
            keys = data.get("keys", [])
            _JWKS_CACHE["keys"] = keys
            _JWKS_CACHE["fetched_at"] = now
            logger.info("Fetched %d JWKS key(s) from Supabase", len(keys))
            return keys
    except Exception as exc:
        logger.error("Failed to fetch Supabase JWKS: %s", exc)
        # Return stale cache rather than failing all requests
        return _JWKS_CACHE.get("keys", [])


# ── User dataclass ────────────────────────────────────────────────────────────

@dataclass
class AuthUser:
    sub: str           # Supabase user UUID
    email: str | None
    role: str | None
    raw: dict          # full JWT payload


# ── Core verifier ─────────────────────────────────────────────────────────────

async def _verify_token(token: str) -> AuthUser:
    """
    Verify a Supabase access-token JWT and return an AuthUser.

    Tries every cached JWKS key until one verifies the token.
    Supports ES256 (new Supabase default) and HS256 (legacy).
    Raises HTTP 401 on any failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        logger.debug("Bad JWT header: %s", exc)
        raise credentials_exception from exc

    alg = unverified_header.get("alg", "ES256")
    kid = unverified_header.get("kid")

    keys = await _get_jwks()

    # Find the key matching the token's kid (if provided)
    matching_keys = [k for k in keys if not kid or k.get("kid") == kid] or keys

    last_exc: Exception = credentials_exception
    for key in matching_keys:
        try:
            payload = jwt.decode(
                token,
                key,
                algorithms=[alg, "ES256", "RS256", "HS256"],
                options={"verify_aud": False},
            )
            return AuthUser(
                sub=payload["sub"],
                email=payload.get("email"),
                role=payload.get("role"),
                raw=payload,
            )
        except JWTError as exc:
            last_exc = exc
            continue

    logger.debug("All JWKS keys failed to verify token: %s", last_exc)
    raise credentials_exception from last_exc


# ── FastAPI dependencies ──────────────────────────────────────────────────────

async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthUser:
    """
    Require a valid Supabase Bearer token.
    Raises HTTP 401 if missing or invalid.
    """
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _verify_token(creds.credentials)


async def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthUser | None:
    """
    Optionally authenticate.  Returns AuthUser or None (never raises).
    """
    if creds is None:
        return None
    try:
        return await _verify_token(creds.credentials)
    except HTTPException:
        return None
