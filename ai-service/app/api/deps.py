"""Dependency injection — auth delegation, Redis, HTTP client."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Annotated

import httpx
import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, status
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

    tenant_id = payload.get("tenant_id", "")
    jti = payload.get("jti") or "_"

    # Check Redis cache — keyed by jti so a logout/refresh invalidates the
    # cached "me" the moment a new access token is issued.
    cache_key = f"ai_svc:me:{user_id}:{jti}"
    cached = await redis.get(cache_key)
    if cached:
        user_data = json.loads(cached)
        # Ensure tenant_id from JWT is always present
        if tenant_id and not user_data.get("tenant_id"):
            user_data["tenant_id"] = tenant_id
        return user_data

    # Fallback to user-service
    try:
        resp = await http_client.get(
            f"{settings.USER_SERVICE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
        if resp.status_code == 200:
            user_data = resp.json()
            # Inject tenant_id from JWT if not present in user-service response
            if tenant_id and not user_data.get("tenant_id"):
                user_data["tenant_id"] = tenant_id
            await redis.setex(cache_key, settings.USER_CACHE_TTL, json.dumps(user_data))
            return user_data
    except httpx.RequestError:
        pass

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user")


CurrentUser = Annotated[dict, Depends(get_current_user)]


_audit_logger = logging.getLogger("superuser_audit")


async def _log_cross_tenant_access(
    user: dict, target_tenant: str, action: str, resource: str | None = None,
) -> None:
    """Log when a superuser accesses another tenant's data."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "superuser_id": user.get("id"),
        "superuser_email": user.get("email"),
        "superuser_tenant": user.get("tenant_id"),
        "target_tenant": target_tenant,
        "action": action,
        "resource": resource,
    }
    _audit_logger.warning("CROSS_TENANT_ACCESS: %s", json.dumps(entry))
    try:
        redis = get_redis()
        key = f"audit:cross_tenant:{datetime.now(timezone.utc).strftime('%Y-%m')}"
        await redis.rpush(key, json.dumps(entry))
        await redis.expire(key, 60 * 60 * 24 * 365)  # keep 1 year
    except Exception:
        pass  # best-effort


def _assert_tenant_access(
    user: dict, tenant_id: str, action: str = "access", resource: str | None = None,
) -> None:
    """Raise 403 if user's tenant_id doesn't match and user is not superuser.
    If superuser accesses another tenant, log it for audit trail."""
    user_tenant = user.get("tenant_id", "")
    if user.get("is_superuser"):
        if user_tenant and user_tenant != tenant_id:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_log_cross_tenant_access(user, tenant_id, action, resource))
            except RuntimeError:
                pass  # no event loop
        return
    if not user_tenant or user_tenant != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: tenant mismatch",
        )


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


async def verify_service_token(
    x_service_token: str = Header(..., alias="X-Service-Token"),
) -> str:
    """Validate inter-service calls via shared secret."""
    settings = get_settings()
    import secrets as _secrets
    if not _secrets.compare_digest(x_service_token or "", settings.S2S_SERVICE_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token")
    return x_service_token


SuperUser = Annotated[dict, Depends(require_superuser)]
ServiceToken = Annotated[str, Depends(verify_service_token)]
