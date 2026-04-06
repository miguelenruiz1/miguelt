"""FastAPI dependency functions shared across routers."""
from __future__ import annotations

import json
import re
import uuid
from typing import Annotated

import httpx
import redis.asyncio as aioredis
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.settings import get_settings
from app.db.session import get_db_session

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


async def get_tenant_id(
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db_session),
) -> uuid.UUID:
    """
    Resolves X-Tenant-Id (slug or UUID string) → validated tenant UUID.

    Caches the resolved UUID on request.state._tenant_id to avoid
    double DB lookups when multiple dependencies call this.
    """
    # Input length validation
    if len(x_tenant_id) > 255:
        raise UnauthorizedError("Invalid tenant identifier")

    # Check cache first
    cached = getattr(request.state, "_tenant_id", None)
    if cached is not None:
        return cached

    from app.db.models import Tenant
    from sqlalchemy import select

    # Try parsing as UUID first, then fall back to slug lookup
    tenant_uuid: uuid.UUID | None = None
    try:
        tenant_uuid = uuid.UUID(x_tenant_id)
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_uuid))
        tenant = result.scalar_one_or_none()
    except ValueError:
        # Not a UUID — treat as slug; validate format
        if not re.match(r'^[a-zA-Z0-9_-]+$', x_tenant_id):
            raise UnauthorizedError("Invalid tenant identifier")
        result = await db.execute(select(Tenant).where(Tenant.slug == x_tenant_id))
        tenant = result.scalar_one_or_none()

    if tenant is None or tenant.status != "active":
        raise UnauthorizedError("Invalid or inactive tenant")

    request.state._tenant_id = tenant.id
    return tenant.id


async def verify_service_token(
    x_service_token: str = Header(..., alias="X-Service-Token"),
) -> str:
    """Validate inter-service shared secret using constant-time comparison."""
    import secrets as _secrets
    settings = get_settings()
    if not _secrets.compare_digest(x_service_token, settings.S2S_SERVICE_TOKEN):
        raise UnauthorizedError("Invalid service token")
    return x_service_token


# ─── JWT auth (mirrors compliance/inventory pattern) ─────────────────────────

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Validate JWT and return user data. Supports S2S bypass via X-Service-Token."""
    settings = get_settings()

    # S2S bypass for inter-service calls
    service_token = request.headers.get("X-Service-Token")
    if service_token:
        import secrets as _secrets
        if _secrets.compare_digest(service_token, settings.S2S_SERVICE_TOKEN):
            return {
                "id": "system",
                "tenant_id": request.headers.get("X-Tenant-Id", "default"),
                "is_superuser": True,
                "permissions": [],
                "email": "system@trace.internal",
            }
        raise UnauthorizedError("Invalid service token")

    # Allow disabling JWT for dev/tests
    if not settings.REQUIRE_AUTH:
        return {
            "id": request.headers.get("X-User-Id", "1"),
            "tenant_id": request.headers.get("X-Tenant-Id", "default"),
            "is_superuser": False,
            "permissions": [],
            "email": "dev@trace.local",
        }

    if credentials is None:
        raise UnauthorizedError("Missing authorization header")

    import jwt
    from jwt import PyJWTError as JWTError
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token missing subject")

    # Cache user data per tenant header so cross-tenant superusers don't share state
    incoming_tid = request.headers.get("X-Tenant-Id", "default")
    rd = await get_redis()
    cache_key = f"trace_svc:me:{user_id}:{incoming_tid}"
    cached = await rd.get(cache_key)
    if cached:
        return json.loads(cached)

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


CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_permission(slug: str):
    async def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("is_superuser"):
            return current_user
        if slug not in (current_user.get("permissions") or []):
            raise ForbiddenError(f"Permission '{slug}' required")
        return current_user
    return Depends(_check)


def require_superuser(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_superuser"):
        raise ForbiddenError("Superuser required")
    return current_user


SuperUser = Annotated[dict, Depends(require_superuser)]
