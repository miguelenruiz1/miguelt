"""Platform administration router — superuser-only endpoints for SaaS management."""
from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_http_client, get_redis
from app.core.settings import get_settings
from app.db.session import get_db_session
from app.services.platform_service import PlatformService

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


def _require_superuser(current_user: CurrentUser) -> dict:
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user


SuperUser = Annotated[dict, Depends(_require_superuser)]


def _svc(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    redis=Depends(get_redis),
) -> PlatformService:
    return PlatformService(db, redis=redis)


# ── Request schemas ──────────────────────────────────────────────────────────

class OnboardTenantRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    admin_email: str = Field(..., min_length=5, max_length=255)
    admin_password: str = Field(..., min_length=6, max_length=128)
    admin_name: str = Field(..., min_length=1, max_length=255)
    plan_slug: str = Field(default="free")
    billing_cycle: str = Field(default="monthly")
    modules: list[str] = Field(default_factory=list)
    notes: str | None = None


class ChangePlanRequest(BaseModel):
    plan_slug: str = Field(..., min_length=1)


class ToggleModuleRequest(BaseModel):
    active: bool


class CancelRequest(BaseModel):
    reason: str | None = None


# ── Dashboard & analytics ────────────────────────────────────────────────────

@router.get("/dashboard")
async def platform_dashboard(
    _: SuperUser,
    svc: PlatformService = Depends(_svc),
):
    return await svc.get_dashboard()


@router.get("/analytics")
async def platform_analytics(
    _: SuperUser,
    svc: PlatformService = Depends(_svc),
    months: int = Query(6, ge=1, le=24),
):
    return await svc.get_analytics(months=months)


@router.get("/sales")
async def platform_sales(
    _: SuperUser,
    svc: PlatformService = Depends(_svc),
):
    return await svc.get_sales_metrics()


# ── Tenant management ────────────────────────────────────────────────────────

@router.get("/tenants")
async def platform_tenants(
    _: SuperUser,
    svc: PlatformService = Depends(_svc),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    plan_slug: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return await svc.list_tenants(
        search=search,
        status=status_filter,
        plan_slug=plan_slug,
        offset=offset,
        limit=limit,
    )


@router.get("/tenants/{tenant_id}")
async def platform_tenant_detail(
    tenant_id: str,
    _: SuperUser,
    svc: PlatformService = Depends(_svc),
):
    detail = await svc.get_tenant_detail(tenant_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return detail


# ── Onboard new tenant ───────────────────────────────────────────────────────

@router.post("/tenants/onboard", status_code=201)
async def onboard_tenant(
    body: OnboardTenantRequest,
    current_user: SuperUser,
    svc: PlatformService = Depends(_svc),
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    try:
        return await svc.onboard_tenant(
            tenant_id=body.tenant_id,
            company_name=body.company_name,
            admin_email=body.admin_email,
            admin_password=body.admin_password,
            admin_name=body.admin_name,
            plan_slug=body.plan_slug,
            billing_cycle=body.billing_cycle,
            modules=body.modules,
            notes=body.notes,
            performed_by=current_user.get("id") or current_user.get("email"),
            http_client=http_client,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ── Tenant subscription actions ──────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/change-plan")
async def change_tenant_plan(
    tenant_id: str,
    body: ChangePlanRequest,
    current_user: SuperUser,
    svc: PlatformService = Depends(_svc),
):
    try:
        return await svc.change_tenant_plan(
            tenant_id=tenant_id,
            plan_slug=body.plan_slug,
            performed_by=current_user.get("id") or current_user.get("email"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tenants/{tenant_id}/modules/{module_slug}")
async def toggle_tenant_module(
    tenant_id: str,
    module_slug: str,
    body: ToggleModuleRequest,
    current_user: SuperUser,
    svc: PlatformService = Depends(_svc),
):
    return await svc.toggle_tenant_module(
        tenant_id=tenant_id,
        module_slug=module_slug,
        active=body.active,
        performed_by=current_user.get("id") or current_user.get("email"),
    )


@router.post("/tenants/{tenant_id}/generate-invoice")
async def generate_tenant_invoice(
    tenant_id: str,
    current_user: SuperUser,
    svc: PlatformService = Depends(_svc),
):
    try:
        return await svc.generate_tenant_invoice(
            tenant_id=tenant_id,
            performed_by=current_user.get("id") or current_user.get("email"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tenants/{tenant_id}/generate-payment-link")
async def generate_payment_link(
    tenant_id: str,
    current_user: SuperUser,
    svc: PlatformService = Depends(_svc),
):
    try:
        return await svc.generate_payment_link(
            tenant_id=tenant_id,
            performed_by=current_user.get("id") or current_user.get("email"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tenants/{tenant_id}/cancel")
async def cancel_tenant_subscription(
    tenant_id: str,
    body: CancelRequest,
    current_user: SuperUser,
    svc: PlatformService = Depends(_svc),
):
    try:
        return await svc.cancel_tenant_subscription(
            tenant_id=tenant_id,
            reason=body.reason,
            performed_by=current_user.get("id") or current_user.get("email"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tenants/{tenant_id}/reactivate")
async def reactivate_tenant_subscription(
    tenant_id: str,
    current_user: SuperUser,
    svc: PlatformService = Depends(_svc),
):
    try:
        return await svc.reactivate_tenant_subscription(
            tenant_id=tenant_id,
            performed_by=current_user.get("id") or current_user.get("email"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Cross-tenant user oversight ─────────────────────────────────────────────

@router.get("/users")
async def platform_list_users(
    current_user: SuperUser,
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    search: str | None = Query(None),
    tenant_id: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List users across all tenants — delegates to user-service."""
    settings = get_settings()
    params: dict = {"offset": offset, "limit": limit}
    if search:
        params["search"] = search
    if tenant_id:
        params["tenant_id"] = tenant_id

    # Forward the superuser's token to user-service
    try:
        # Use internal user-service URL
        resp = await http_client.get(
            f"{settings.USER_SERVICE_URL}/api/v1/users/all",
            params=params,
            headers={"Authorization": f"Bearer {_extract_token(current_user)}"},
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User service unavailable",
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch users")
    return resp.json()


def _extract_token(user_dict: dict) -> str:
    """Best-effort extraction of the bearer token from the cached user dict."""
    return user_dict.get("_token", "")


@router.post("/check-expirations", summary="Run subscription expiration check manually")
async def check_expirations_endpoint(
    _user: SuperUser,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Manually trigger subscription expiration check. Normally runs hourly in background."""
    from app.services.expiration_service import check_expirations
    summary = await check_expirations(db)
    return {"status": "ok", **summary}
