"""Batch plot-origin endpoints (cross-DB lineage to compliance_plots)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.quality_test import BatchPlotOriginCreate, BatchPlotOriginOut
from app.services.batch_origin_service import BatchOriginService

router = APIRouter(tags=["batch-origins"])


def _svc(db: AsyncSession = Depends(get_db_session)) -> BatchOriginService:
    return BatchOriginService(db)


@router.post(
    "/api/v1/batches/{batch_id}/origins",
    response_model=BatchPlotOriginOut,
    status_code=201,
)
async def create_origin(
    batch_id: str,
    body: BatchPlotOriginCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    svc: BatchOriginService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.create(tenant_id, batch_id, body.model_dump())


@router.get(
    "/api/v1/batches/{batch_id}/origins",
    response_model=list[BatchPlotOriginOut],
)
async def list_origins(
    batch_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: BatchOriginService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.list_for_batch(tenant_id, batch_id)
