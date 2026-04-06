"""Modules router — activate/deactivate tenant modules."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db_session
from app.services.module_service import ModuleService

router = APIRouter(prefix="/api/v1/modules", tags=["modules"])


def _svc(db: Annotated[AsyncSession, Depends(get_db_session)]) -> ModuleService:
    return ModuleService(db)


@router.get("/", summary="Module catalogue (public)")
async def list_catalog(svc: ModuleService = Depends(_svc)):
    return svc.get_catalog()


@router.get("/{tenant_id}", summary="Module status for tenant (public)")
async def list_tenant_modules(
    tenant_id: str,
    svc: ModuleService = Depends(_svc),
):
    return await svc.list_tenant_modules(tenant_id)


@router.get("/{tenant_id}/{slug}", summary="Single module status (inter-service, no auth)")
async def get_module_status(
    tenant_id: str,
    slug: str,
    svc: ModuleService = Depends(_svc),
):
    is_active = await svc.is_active(tenant_id, slug)
    return {"tenant_id": tenant_id, "slug": slug, "is_active": is_active}


def _enforce_tenant(current_user: dict, path_tenant_id: str) -> None:
    if current_user.get("is_superuser"):
        return
    user_tenant = str(current_user.get("tenant_id", "default"))
    if str(path_tenant_id) != user_tenant:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied to other tenant's modules")


@router.post("/{tenant_id}/{slug}/activate", summary="Activate module")
async def activate_module(
    tenant_id: str,
    slug: str,
    current_user: Annotated[dict, Depends(require_permission("subscription.manage"))],
    svc: ModuleService = Depends(_svc),
):
    _enforce_tenant(current_user, tenant_id)
    performed_by = current_user.get("id") or current_user.get("email")
    record = await svc.activate(tenant_id, slug, performed_by=performed_by)
    return {"tenant_id": tenant_id, "slug": slug, "is_active": record.is_active}


@router.post("/{tenant_id}/{slug}/deactivate", summary="Deactivate module")
async def deactivate_module(
    tenant_id: str,
    slug: str,
    current_user: Annotated[dict, Depends(require_permission("subscription.manage"))],
    svc: ModuleService = Depends(_svc),
):
    _enforce_tenant(current_user, tenant_id)
    performed_by = current_user.get("id") or current_user.get("email")
    record = await svc.deactivate(tenant_id, slug, performed_by=performed_by)
    return {"tenant_id": tenant_id, "slug": slug, "is_active": record.is_active}
