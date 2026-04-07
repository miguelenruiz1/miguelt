"""FastAPI dependencies for integration-service: auth delegation."""
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
        _http_client = httpx.AsyncClient(timeout=15.0)
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

    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_exception

    # Key by jti so logout/refresh invalidates the cached "me" immediately.
    jti = payload.get("jti") or "_"
    cache_key = f"int_svc:me:{user_id}:{jti}"
    settings = get_settings()
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

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
    await redis.setex(cache_key, settings.USER_CACHE_TTL, json.dumps(user_data))
    return user_data


CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_permission(slug: str):
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
