"""FastAPI dependencies for inventory-service: auth delegation + module gate."""
from __future__ import annotations

import json
from typing import Annotated

import httpx
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

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

    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_exception

    cache_key = f"inv_svc:me:{user_id}"
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


async def require_inventory_module(
    current_user: CurrentUser,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> dict:
    """Gate: verify the inventory module is active for this tenant."""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant context")

    settings = get_settings()
    cache_key = f"module:{tenant_id}:{settings.MODULE_SLUG}"

    cached = await redis.get(cache_key)
    if cached == "1":
        return current_user
    if cached == "0":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Módulo Inventario no activado para este tenant",
        )

    try:
        resp = await http_client.get(
            f"{settings.SUBSCRIPTION_SERVICE_URL}/api/v1/modules/{tenant_id}/{settings.MODULE_SLUG}"
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo verificar el módulo de inventario. Intente más tarde.",
        )

    active = resp.status_code == 200 and resp.json().get("is_active", False)
    await redis.setex(cache_key, settings.MODULE_CACHE_TTL, "1" if active else "0")

    if not active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Módulo Inventario no activado para este tenant",
        )
    return current_user


ModuleUser = Annotated[dict, Depends(require_inventory_module)]


async def require_production_module(
    current_user: CurrentUser,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> dict:
    """Gate that checks both 'inventory' AND 'production' modules are active."""
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant context")

    settings = get_settings()

    for slug in ("inventory", "production"):
        cache_key = f"module:{tenant_id}:{slug}"
        cached = await redis.get(cache_key)
        if cached == "1":
            continue
        if cached == "0":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Module '{slug}' is not active for this tenant",
            )

        # Fallback to subscription-service
        try:
            resp = await http_client.get(
                f"{settings.SUBSCRIPTION_SERVICE_URL}/api/v1/modules/{tenant_id}/{slug}"
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No se pudo verificar el módulo '{slug}'. Intente más tarde.",
            )

        active = resp.status_code == 200 and resp.json().get("is_active", False)
        await redis.setex(cache_key, settings.MODULE_CACHE_TTL, "1" if active else "0")

        if not active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Module '{slug}' is not active for this tenant",
            )

    return current_user


ProductionModuleUser = Annotated[dict, Depends(require_production_module)]


async def is_einvoicing_active(
    tenant_id: str,
    redis: aioredis.Redis | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> bool:
    """Check if electronic-invoicing module is active for this tenant (non-blocking)."""
    if redis is None:
        redis = get_redis()
    if http_client is None:
        http_client = get_http_client()
    settings = get_settings()
    cache_key = f"module:{tenant_id}:electronic-invoicing"

    cached = await redis.get(cache_key)
    if cached == "1":
        return True
    if cached == "0":
        return False

    try:
        resp = await http_client.get(
            f"{settings.SUBSCRIPTION_SERVICE_URL}/api/v1/modules/{tenant_id}/electronic-invoicing"
        )
    except httpx.RequestError:
        return False

    active = resp.status_code == 200 and resp.json().get("is_active", False)
    await redis.setex(cache_key, settings.MODULE_CACHE_TTL, "1" if active else "0")
    return active


async def is_einvoicing_sandbox_active(
    tenant_id: str,
    redis: aioredis.Redis | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> bool:
    """Check if electronic-invoicing-sandbox module is active for this tenant (non-blocking)."""
    if redis is None:
        redis = get_redis()
    if http_client is None:
        http_client = get_http_client()
    settings = get_settings()
    cache_key = f"module:{tenant_id}:electronic-invoicing-sandbox"

    cached = await redis.get(cache_key)
    if cached == "1":
        return True
    if cached == "0":
        return False

    try:
        resp = await http_client.get(
            f"{settings.SUBSCRIPTION_SERVICE_URL}/api/v1/modules/{tenant_id}/electronic-invoicing-sandbox"
        )
    except httpx.RequestError:
        return False

    active = resp.status_code == 200 and resp.json().get("is_active", False)
    await redis.setex(cache_key, settings.MODULE_CACHE_TTL, "1" if active else "0")
    return active
