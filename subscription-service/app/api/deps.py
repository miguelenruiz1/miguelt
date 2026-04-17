"""FastAPI dependencies for subscription-service auth delegation."""
from __future__ import annotations

import json
from typing import Annotated

import httpx
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError as JWTError

from app.core.security import decode_token
from app.core.settings import get_settings

_bearer = HTTPBearer(auto_error=True)
_bearer_optional = HTTPBearer(auto_error=False)

_redis_client: aioredis.Redis | None = None
_http_client: httpx.AsyncClient | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> dict:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Decode JWT locally
    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    # 2. Verify it's an access token
    if payload.get("type") != "access":
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_exception

    # 3. Check Redis cache — keyed by jti so a logout (which rotates the jti
    # via refresh, or blacklists the current one) invalidates the cache the
    # moment the next access token is issued. Without jti in the key, a stale
    # cached "me" survives logout for the full TTL window.
    jti = payload.get("jti") or "_"
    cache_key = f"sub_svc:me:{user_id}:{jti}"
    settings = get_settings()
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        data["_token"] = token
        data["2fa"] = bool(payload.get("2fa"))  # FASE4
        return data

    # 4. Delegate to user-service
    try:
        resp = await http_client.get(
            f"{settings.USER_SERVICE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User service unavailable",
        )

    if resp.status_code != 200:
        raise credentials_exception

    user_data = resp.json()

    # 5. Cache for TTL seconds (never persist the raw bearer token to Redis)
    await redis.setex(cache_key, settings.USER_CACHE_TTL, json.dumps(user_data))

    user_data["_token"] = token
    # FASE4: propagate the `2fa` claim from the JWT so superuser routes that
    # require 2FA can enforce REQUIRE_SUPERUSER_2FA. Not cached in Redis
    # (user-service /me doesn't know whether THIS token was 2FA-completed).
    user_data["2fa"] = bool(payload.get("2fa"))
    return user_data


CurrentUser = Annotated[dict, Depends(get_current_user)]


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_optional)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> dict | None:
    """Same as get_current_user but returns None when no Authorization header.

    Used by endpoints that accept EITHER authenticated users OR alternate
    credentials (e.g. an inter-service X-Service-Token). Returning None lets
    the caller decide how to handle anonymous requests.
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, redis, http_client)
    except HTTPException:
        return None


def require_permission(slug: str):
    """Returns a callable suitable for Depends() that checks a permission slug."""
    async def _check(current_user: CurrentUser) -> dict:
        if current_user.get("is_superuser"):
            return current_user
        perms = current_user.get("permissions", [])
        if slug not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {slug}",
            )
        return current_user
    return _check
