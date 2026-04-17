"""FastAPI dependencies: tenant resolution, JWT auth, and S2S validation."""
from __future__ import annotations

import json
import secrets as _secrets
import uuid
from typing import Annotated

import httpx
import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.settings import get_settings

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


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Validate JWT and return user data. Supports S2S bypass via X-Service-Token."""
    settings = get_settings()

    # S2S bypass for inter-service calls
    service_token = request.headers.get("X-Service-Token")
    if service_token:
        if _secrets.compare_digest(service_token, settings.S2S_SERVICE_TOKEN):
            tid_header = request.headers.get("X-Tenant-Id", "")
            return {
                "id": "system",
                "tenant_id": tid_header,
                "is_superuser": True,
                "permissions": [],
                "email": "system@trace.internal",
            }
        raise HTTPException(status_code=401, detail="Invalid service token")

    if not settings.REQUIRE_AUTH:
        return {
            "id": request.headers.get("X-User-Id", "1"),
            "tenant_id": request.headers.get("X-Tenant-Id", "default"),
            "is_superuser": False,
            "permissions": [],
            "email": "dev@trace.local",
        }

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    import jwt
    from jwt import PyJWTError as JWTError
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    incoming_tid = request.headers.get("X-Tenant-Id", "default")
    rd = await get_redis()
    jti = payload.get("jti") or "_"
    cache_key = f"media_svc:me:{user_id}:{incoming_tid}:{jti}"
    cached = await rd.get(cache_key)
    if cached:
        return json.loads(cached)

    http = get_http_client()
    resp = await http.get(
        f"{settings.USER_SERVICE_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="User not found or token expired")

    user_data = resp.json()
    await rd.setex(cache_key, settings.USER_CACHE_TTL, json.dumps(user_data))
    return user_data


async def get_tenant_id(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> uuid.UUID:
    """Resolve tenant from authenticated user (NOT from client header).

    The JWT is signed by user-service so whatever tenant_id it carries —
    UUID or slug — is already trusted. We used to reject slug tenants unless
    an X-Service-Token was also present, but regular users never send that
    header, so registration of any non-"default" tenant broke every media
    request with 400. Slug → UUID mapping uses uuid5 in a fixed namespace so
    every service resolves the same slug to the same UUID.
    """
    raw = str(current_user.get("tenant_id", "")).strip()
    if not raw:
        raise HTTPException(status_code=400, detail="No tenant in user token")
    if len(raw) > 255:
        raise HTTPException(status_code=400, detail="Invalid tenant identifier")
    try:
        return uuid.UUID(raw)
    except ValueError:
        if raw == "default":
            return uuid.UUID("00000000-0000-0000-0000-000000000001")
        return uuid.uuid5(uuid.NAMESPACE_DNS, raw)


async def verify_service_token(
    x_service_token: str = Header(..., alias="X-Service-Token"),
) -> str:
    """Validate inter-service shared secret using constant-time comparison."""
    settings = get_settings()
    if not _secrets.compare_digest(x_service_token, settings.S2S_SERVICE_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


CurrentUser = Annotated[dict, Depends(get_current_user)]
