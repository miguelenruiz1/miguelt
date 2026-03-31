"""Dependencies: JWT auth, module gating, tenant resolution."""
from __future__ import annotations

import json
import uuid
from typing import Annotated

import httpx
import redis.asyncio as aioredis
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import ForbiddenError, ModuleNotActiveError, UnauthorizedError
from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

_http: httpx.AsyncClient | None = None
_redis: aioredis.Redis | None = None
_bearer = HTTPBearer(auto_error=False)


def get_http_client() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(timeout=10.0)
    return _http


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _redis


# ─── Tenant resolution ────────────────────────────────────────────────────────

async def get_tenant_id(request: Request) -> uuid.UUID:
    slug = getattr(request.state, "tenant_slug", None) or "default"
    try:
        return uuid.UUID(slug)
    except ValueError:
        http = get_http_client()
        settings = get_settings()
        resp = await http.get(
            f"{settings.TRACE_SERVICE_URL}/api/v1/tenants",
            headers={"X-Tenant-Id": slug},
        )
        if resp.status_code == 200:
            for t in resp.json():
                if t.get("slug") == slug:
                    return uuid.UUID(t["id"])
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


# ─── JWT auth (same pattern as inventory-service) ─────────────────────────────

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    # Allow S2S calls with X-Service-Token (bypass JWT)
    service_token = request.headers.get("X-Service-Token")
    if service_token:
        settings = get_settings()
        if service_token == settings.S2S_SERVICE_TOKEN:
            tenant_id = request.headers.get("X-Tenant-Id", "default")
            return {
                "id": "system",
                "tenant_id": tenant_id,
                "is_superuser": True,
                "permissions": [],
                "email": "system@trace.internal",
            }
        raise UnauthorizedError("Invalid service token")

    if credentials is None:
        raise UnauthorizedError("Missing authorization header")

    settings = get_settings()
    token = credentials.credentials

    from jose import JWTError, jwt

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token missing subject")

    # Redis cache
    rd = await get_redis()
    cache_key = f"cmp_svc:me:{user_id}"
    cached = await rd.get(cache_key)
    if cached:
        return json.loads(cached)

    # Delegate to user-service
    http = get_http_client()
    resp = await http.get(
        f"{settings.USER_SERVICE_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code != 200:
        raise UnauthorizedError("User not found or token expired")

    user_data = resp.json()
    await rd.setex(cache_key, settings.USER_CACHE_TTL, json.dumps(user_data))
    return user_data


def require_permission(slug: str):
    async def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("is_superuser"):
            return current_user
        perms = current_user.get("permissions", [])
        if slug not in perms:
            raise ForbiddenError(f"Permission '{slug}' required")
        return current_user
    return Depends(_check)


# ─── Module gating ────────────────────────────────────────────────────────────

async def require_compliance_module(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    settings = get_settings()
    tenant_id = current_user.get("tenant_id", "default")
    module_slug = settings.MODULE_SLUG
    cache_key = f"module:{tenant_id}:{module_slug}"

    rd = await get_redis()
    cached = await rd.get(cache_key)
    if cached == "1":
        return current_user
    if cached == "0":
        raise ModuleNotActiveError(module_slug)

    http = get_http_client()
    try:
        resp = await http.get(
            f"{settings.SUBSCRIPTION_SERVICE_URL}/api/v1/modules/{tenant_id}/{module_slug}",
        )
        active = resp.status_code == 200 and resp.json().get("is_active", False)
    except Exception:
        active = False

    await rd.setex(cache_key, settings.MODULE_CACHE_TTL, "1" if active else "0")

    if not active:
        raise ModuleNotActiveError(module_slug)
    return current_user


ModuleUser = Annotated[dict, Depends(require_compliance_module)]
SuperUser = Annotated[dict, Depends(get_current_user)]
