"""Licenses router."""
from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_redis, require_permission
from app.db.session import get_db_session
from app.domain.schemas import IssueKeyRequest, LicenseKeyResponse
from app.services.license_service import LicenseService

router = APIRouter(prefix="/api/v1/licenses", tags=["licenses"])

# Public validate endpoint needs a brute-force brake. Sliding window: N hits
# per IP per WINDOW seconds. Lives in Redis so it survives pod restarts and
# is shared across replicas. slowapi isn't wired in this service and the
# counter is trivial enough to inline.
_RATE_LIMIT_MAX = 20
_RATE_LIMIT_WINDOW_SECONDS = 60


def _svc(db: Annotated[AsyncSession, Depends(get_db_session)]) -> LicenseService:
    return LicenseService(db)


async def _rate_limit_validate(request: Request, redis: aioredis.Redis) -> None:
    ip = (
        (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    key = f"ratelimit:license-validate:{ip}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, _RATE_LIMIT_WINDOW_SECONDS)
    except Exception:
        # Redis hiccup → fail open. Rate limit is defense-in-depth; the real
        # brake is that keys have 128 bits of entropy.
        return
    if count > _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({_RATE_LIMIT_MAX}/{_RATE_LIMIT_WINDOW_SECONDS}s)",
        )


@router.get("/", response_model=list[LicenseKeyResponse])
async def list_licenses(
    current_user: Annotated[dict, Depends(require_permission("subscription.view"))],
    tenant_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    svc: LicenseService = Depends(_svc),
):
    # Non-superusers can only see their own tenant's licenses
    if not current_user.get("is_superuser"):
        tenant_id = current_user.get("tenant_id", "default")
    return await svc.list(tenant_id=tenant_id, status=status, offset=offset, limit=limit)


@router.post("/", response_model=LicenseKeyResponse, status_code=201)
async def issue_license(
    body: IssueKeyRequest,
    _: Annotated[dict, Depends(require_permission("subscription.manage"))],
    svc: LicenseService = Depends(_svc),
):
    return await svc.issue(body.model_dump())


@router.get("/validate/{key}")
async def validate_license(
    key: str,
    request: Request,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    svc: LicenseService = Depends(_svc),
):
    """Public endpoint — no authentication required. Rate-limited per IP."""
    await _rate_limit_validate(request, redis)
    return await svc.validate(key)


@router.get("/{lic_id}", response_model=LicenseKeyResponse)
async def get_license(
    lic_id: str,
    current_user: Annotated[dict, Depends(require_permission("subscription.view"))],
    svc: LicenseService = Depends(_svc),
):
    scope_tid = None if current_user.get("is_superuser") else current_user.get("tenant_id")
    return await svc.get(lic_id, tenant_id=scope_tid)


@router.post("/{lic_id}/revoke", status_code=204)
async def revoke_license(
    lic_id: str,
    current_user: Annotated[dict, Depends(require_permission("subscription.manage"))],
    svc: LicenseService = Depends(_svc),
):
    revoked_by = current_user.get("id") or current_user.get("email")
    scope_tid = None if current_user.get("is_superuser") else current_user.get("tenant_id")
    await svc.revoke(lic_id, revoked_by=revoked_by, tenant_id=scope_tid)
