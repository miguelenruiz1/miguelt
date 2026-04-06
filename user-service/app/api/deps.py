"""FastAPI dependencies for authentication and authorization."""
from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.settings import get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.repositories.user_repo import UserRepository

_bearer = HTTPBearer(auto_error=True)

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
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

    # Check blacklist
    redis = get_redis()
    blacklisted = await redis.exists(f"blacklist:access:{token}")
    if blacklisted:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise credentials_exception

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(slug: str):
    """Returns a dependency that checks for a specific permission slug."""
    async def _check(
        current_user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        if current_user.is_superuser:
            return current_user
        repo = UserRepository(db)
        permissions = await repo.get_user_permissions(current_user.id)
        if slug not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {slug}",
            )
        return current_user
    return Depends(_check)


def get_tenant_id(request: Request) -> str:
    """Read X-Tenant-Id header, default to 'default'."""
    return request.headers.get("X-Tenant-Id", "default")


# ─── Rate limiting (Redis-backed sliding window) ────────────────────────────


async def rate_limit(
    request: Request,
    bucket: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    """Token-bucket-ish rate limit keyed by `bucket:client_ip`.

    Raises HTTP 429 when the IP exceeds `max_requests` in `window_seconds`.

    Used on hot login/refresh/register/forgot-password endpoints to prevent
    brute force and email enumeration.
    """
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    key = f"rl:{bucket}:{client_ip}"
    rd = get_redis()
    try:
        # Atomic INCR + EXPIRE on first hit
        count = await rd.incr(key)
        if count == 1:
            await rd.expire(key, window_seconds)
        if count > max_requests:
            ttl = await rd.ttl(key)
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again in {max(ttl, 1)}s.",
                headers={"Retry-After": str(max(ttl, 1))},
            )
    except HTTPException:
        raise
    except Exception:
        # Fail open: if Redis is down, don't block legitimate users.
        pass


async def login_rate_limit(request: Request) -> None:
    """5 login attempts per IP per 15 minutes."""
    await rate_limit(request, "login", 5, 900)


async def register_rate_limit(request: Request) -> None:
    """10 register attempts per IP per hour (anti DoS / spam)."""
    await rate_limit(request, "register", 10, 3600)


async def password_reset_rate_limit(request: Request) -> None:
    """3 password reset requests per IP per hour."""
    await rate_limit(request, "pwreset", 3, 3600)
