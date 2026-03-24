"""Usage and enforcement router."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.api.deps import get_http_client, require_permission
from app.db.session import get_db_session
from app.enforcement.plan_enforcer import PlanEnforcer
from app.enforcement.schemas import UsageSummary

router = APIRouter(tags=["usage"])


def _enforcer(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> PlanEnforcer:
    return PlanEnforcer(db, http_client)


@router.get(
    "/api/v1/usage/{tenant_id}",
    response_model=UsageSummary,
    summary="Usage summary for a tenant",
)
async def get_usage(
    tenant_id: str,
    _: Annotated[dict, Depends(require_permission("subscription.view"))],
    enforcer: PlanEnforcer = Depends(_enforcer),
) -> UsageSummary:
    return await enforcer.get_usage_summary(tenant_id)


@router.get(
    "/api/v1/enforcement/check/{tenant_id}/{resource}",
    summary="Check if tenant can create resource (inter-service, no auth)",
)
async def check_enforcement(
    tenant_id: str,
    resource: str,
    enforcer: PlanEnforcer = Depends(_enforcer),
) -> dict:
    """Inter-service endpoint. Returns {allowed: true} or raises 402."""
    checkers = {
        "users": enforcer.check_can_create_user,
        "assets": enforcer.check_can_create_asset,
        "wallets": enforcer.check_can_create_wallet,
    }
    checker = checkers.get(resource)
    if checker is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown resource: {resource}. Valid: {', '.join(checkers)}",
        )
    await checker(tenant_id)
    return {"allowed": True, "resource": resource, "tenant_id": tenant_id}
