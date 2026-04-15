"""Batch quality tests endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.quality_test import QualityTestCreate, QualityTestOut
from app.services.quality_test_service import QualityTestService

router = APIRouter(tags=["quality-tests"])


def _svc(db: AsyncSession = Depends(get_db_session)) -> QualityTestService:
    return QualityTestService(db)


@router.post("/api/v1/quality-tests", response_model=QualityTestOut, status_code=201)
async def create_quality_test(
    body: QualityTestCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    svc: QualityTestService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.create(tenant_id, body.model_dump())


@router.get(
    "/api/v1/batches/{batch_id}/quality-tests",
    response_model=list[QualityTestOut],
)
async def list_quality_tests(
    batch_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: QualityTestService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.list_for_batch(tenant_id, batch_id)
