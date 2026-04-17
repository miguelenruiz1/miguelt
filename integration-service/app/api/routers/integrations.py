"""Integration config, sync, and invoicing endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import INTEGRATION_CATALOG
from app.api.deps import CurrentUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.integration import (
    CreateInvoiceRequest, IntegrationConfigCreate, IntegrationConfigOut,
    IntegrationConfigUpdate, PaginatedSyncJobs, SyncJobOut, SyncLogOut,
    SyncRequest, TestConnectionRequest,
)
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

Viewer = Annotated[dict, Depends(require_permission("integrations.view"))]
Manager = Annotated[dict, Depends(require_permission("integrations.manage"))]


# ── Catalog (public — no auth needed) ──────────────────────────────
@router.get("/catalog")
async def integration_catalog():
    """List all available integration providers."""
    return INTEGRATION_CATALOG


# ── Integration Configs ─────────────────────────────────────────────
@router.get("", response_model=list[IntegrationConfigOut])
async def list_integrations(
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = IntegrationService(db)
    return await svc.list_configs(user["tenant_id"])


@router.get("/{config_id}", response_model=IntegrationConfigOut)
async def get_integration(
    config_id: str,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = IntegrationService(db)
    return await svc.get_config(config_id, user["tenant_id"])


@router.post("", response_model=IntegrationConfigOut, status_code=201)
async def create_or_update_integration(
    body: IntegrationConfigCreate,
    user: Manager,
    db: AsyncSession = Depends(get_db_session),
):
    svc = IntegrationService(db)
    return await svc.upsert_config(user["tenant_id"], body.model_dump(), user.get("id"))


@router.patch("/{config_id}", response_model=IntegrationConfigOut)
async def update_integration(
    config_id: str,
    body: IntegrationConfigUpdate,
    user: Manager,
    db: AsyncSession = Depends(get_db_session),
):
    svc = IntegrationService(db)
    config = await svc.get_config(config_id, user["tenant_id"])
    data = body.model_dump(exclude_unset=True)
    credentials = data.pop("credentials", None)
    if credentials is not None:
        import json
        from app.core.security import encrypt_credentials
        data["credentials_enc"] = encrypt_credentials(json.dumps(credentials))
    data["updated_by"] = user.get("id")
    from app.repositories.integration_repo import IntegrationConfigRepository
    repo = IntegrationConfigRepository(db)
    real = await repo.get(config_id, user["tenant_id"])
    result = await repo.upsert({**{"tenant_id": user["tenant_id"], "provider_slug": real.provider_slug}, **data})
    result.credentials_enc = None
    return result


@router.delete("/{config_id}", status_code=204)
async def delete_integration(
    config_id: str,
    user: Manager,
    db: AsyncSession = Depends(get_db_session),
):
    svc = IntegrationService(db)
    await svc.delete_config(config_id, user["tenant_id"])


# ── Test Connection ─────────────────────────────────────────────────
@router.post("/{provider_slug}/test")
async def test_connection(
    provider_slug: str,
    user: Manager,
    db: AsyncSession = Depends(get_db_session),
    body: TestConnectionRequest | None = None,
):
    svc = IntegrationService(db)
    creds = body.credentials if body else None
    return await svc.test_connection(user["tenant_id"], provider_slug, creds)


# ── Sync ────────────────────────────────────────────────────────────
@router.post("/{provider_slug}/sync", response_model=SyncJobOut)
async def trigger_sync(
    provider_slug: str,
    body: SyncRequest,
    user: Manager,
    db: AsyncSession = Depends(get_db_session),
):
    svc = IntegrationService(db)
    return await svc.sync(
        user["tenant_id"], provider_slug,
        body.direction, body.entity_type, user.get("id"),
    )


@router.get("/sync-jobs", response_model=PaginatedSyncJobs)
async def list_sync_jobs(
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    provider_slug: str | None = None,
    status: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    svc = IntegrationService(db)
    items, total = await svc.list_sync_jobs(
        user["tenant_id"], provider_slug=provider_slug, status=status,
        offset=offset, limit=limit,
    )
    return PaginatedSyncJobs(items=items, total=total, offset=offset, limit=limit)


@router.get("/sync-jobs/{job_id}/logs", response_model=list[SyncLogOut])
async def get_sync_job_logs(
    job_id: str,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    svc = IntegrationService(db)
    return await svc.get_sync_job_logs(job_id, user["tenant_id"], offset, limit)


# ── Invoicing ───────────────────────────────────────────────────────
@router.post("/{provider_slug}/invoices")
async def create_invoice(
    provider_slug: str,
    body: CreateInvoiceRequest,
    user: Manager,
    db: AsyncSession = Depends(get_db_session),
):
    svc = IntegrationService(db)
    return await svc.create_invoice(user["tenant_id"], provider_slug, body.model_dump(), user.get("id"))


@router.get("/{provider_slug}/invoices/{remote_id}")
async def get_remote_invoice(
    provider_slug: str,
    remote_id: str,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = IntegrationService(db)
    return await svc.get_invoice(user["tenant_id"], provider_slug, remote_id)


@router.get("/{provider_slug}/invoices")
async def list_remote_invoices(
    provider_slug: str,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    svc = IntegrationService(db)
    return await svc.list_remote_invoices(
        user["tenant_id"], provider_slug, {"page": page, "page_size": page_size}
    )
