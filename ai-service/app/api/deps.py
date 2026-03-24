"""Dependency injection — auth delegation, Redis, HTTP client."""
from __future__ import annotations

from typing import Annotated

import httpx
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.core.settings import get_settings

_bearer = HTTPBearer(auto_error=False)
_redis_client: aioredis.Redis | None = None
_http_client: httpx.AsyncClient | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _redis_client


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    settings = get_settings()
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # Check Redis cache
    cache_key = f"ai_svc:me:{user_id}"
    cached = await redis.get(cache_key)
    if cached:
        import json
        return json.loads(cached)

    # Fallback to user-service
    try:
        resp = await http_client.get(
            f"{settings.USER_SERVICE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
        if resp.status_code == 200:
            user_data = resp.json()
            import json
            await redis.setex(cache_key, settings.USER_CACHE_TTL, json.dumps(user_data))
            return user_data
    except httpx.RequestError:
        pass

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user")


CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_permission(slug: str):
    async def _check(current_user: CurrentUser) -> dict:
        if current_user.get("is_superuser"):
            return current_user
        if slug not in current_user.get("permissions", []):
            raise HTTPException(status_code=403, detail=f"Permission required: {slug}")
        return current_user
    return _check


def require_superuser(current_user: CurrentUser) -> dict:
    if not current_user.get("is_superuser"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superuser access required")
    return current_user


SuperUser = Annotated[dict, Depends(require_superuser)]
