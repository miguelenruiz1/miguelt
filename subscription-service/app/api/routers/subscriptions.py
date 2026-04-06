"""Subscriptions router."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db_session
from app.domain.schemas import (
    CancelRequest,
    InvoiceResponse,
    MarkPaidRequest,
    PaginatedResponse,
    SubscriptionCreate,
    SubscriptionEventResponse,
    SubscriptionResponse,
    UpgradeRequest,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])


def _svc(db: Annotated[AsyncSession, Depends(get_db_session)]) -> SubscriptionService:
    return SubscriptionService(db)


@router.get("/", response_model=PaginatedResponse[SubscriptionResponse])
async def list_subscriptions(
    current_user: Annotated[dict, Depends(require_permission("subscription.view"))],
    status: str | None = Query(default=None),
    plan_id: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    svc: SubscriptionService = Depends(_svc),
):
    # Non-superusers can only see their own tenant's subscription
    if not current_user.get("is_superuser"):
        tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list(
        status=status,
        plan_id=plan_id,
        tenant_id=tenant_id,
        offset=offset,
        limit=limit,
    )
    return PaginatedResponse(items=items, total=total, offset=offset, limit=limit)


@router.post("/", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    body: SubscriptionCreate,
    current_user: Annotated[dict, Depends(require_permission("subscription.manage"))],
    svc: SubscriptionService = Depends(_svc),
):
    data = body.model_dump()
    data["performed_by"] = current_user.get("id") or current_user.get("email")
    return await svc.create(data)


def _enforce_tenant_match(current_user: dict, path_tenant_id: str) -> None:
    """Reject path tenant_id != JWT tenant_id unless caller is superuser.

    Closes IDOR where any tenant admin could mutate other tenants by manipulating
    the path. Superusers may operate cross-tenant intentionally.
    """
    if current_user.get("is_superuser"):
        return
    user_tenant = str(current_user.get("tenant_id", "default"))
    if str(path_tenant_id) != user_tenant:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied to other tenant's resources")


@router.get("/{tenant_id}", response_model=SubscriptionResponse)
async def get_subscription(
    tenant_id: str,
    current_user: Annotated[dict, Depends(require_permission("subscription.view"))],
    svc: SubscriptionService = Depends(_svc),
):
    _enforce_tenant_match(current_user, tenant_id)
    return await svc.get(tenant_id)


@router.patch("/{tenant_id}", response_model=SubscriptionResponse)
async def upgrade_subscription(
    tenant_id: str,
    body: UpgradeRequest,
    current_user: Annotated[dict, Depends(require_permission("subscription.manage"))],
    svc: SubscriptionService = Depends(_svc),
):
    _enforce_tenant_match(current_user, tenant_id)
    performed_by = current_user.get("id") or current_user.get("email")
    return await svc.upgrade(tenant_id, body.plan_slug, performed_by=performed_by)


@router.post("/{tenant_id}/cancel", status_code=204)
async def cancel_subscription(
    tenant_id: str,
    body: CancelRequest,
    current_user: Annotated[dict, Depends(require_permission("subscription.manage"))],
    svc: SubscriptionService = Depends(_svc),
):
    _enforce_tenant_match(current_user, tenant_id)
    performed_by = current_user.get("id") or current_user.get("email")
    await svc.cancel(tenant_id, reason=body.reason, performed_by=performed_by)


@router.post("/{tenant_id}/reactivate", response_model=SubscriptionResponse)
async def reactivate_subscription(
    tenant_id: str,
    current_user: Annotated[dict, Depends(require_permission("subscription.manage"))],
    svc: SubscriptionService = Depends(_svc),
):
    _enforce_tenant_match(current_user, tenant_id)
    performed_by = current_user.get("id") or current_user.get("email")
    return await svc.reactivate(tenant_id, performed_by=performed_by)


@router.get("/{tenant_id}/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    tenant_id: str,
    current_user: Annotated[dict, Depends(require_permission("subscription.view"))],
    svc: SubscriptionService = Depends(_svc),
):
    _enforce_tenant_match(current_user, tenant_id)
    return await svc.get_invoices(tenant_id)


@router.post("/{tenant_id}/invoices", response_model=InvoiceResponse, status_code=201)
async def generate_invoice(
    tenant_id: str,
    current_user: Annotated[dict, Depends(require_permission("subscription.manage"))],
    svc: SubscriptionService = Depends(_svc),
):
    performed_by = current_user.get("id") or current_user.get("email")
    return await svc.generate_invoice(tenant_id, performed_by=performed_by)


@router.patch("/{tenant_id}/invoices/{inv_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    tenant_id: str,
    inv_id: str,
    body: MarkPaidRequest,
    current_user: Annotated[dict, Depends(require_permission("subscription.manage"))],
    svc: SubscriptionService = Depends(_svc),
):
    performed_by = current_user.get("id") or current_user.get("email")
    return await svc.mark_invoice_paid(tenant_id, inv_id, performed_by=performed_by)


@router.get("/{tenant_id}/events", response_model=list[SubscriptionEventResponse])
async def list_events(
    tenant_id: str,
    _: Annotated[dict, Depends(require_permission("subscription.view"))],
    svc: SubscriptionService = Depends(_svc),
):
    return await svc.get_events(tenant_id)
