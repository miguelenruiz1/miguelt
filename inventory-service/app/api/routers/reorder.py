"""Auto-reorder endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.purchase_order import POOut
from app.services.reorder_service import ReorderService

router = APIRouter(prefix="/api/v1/reorder", tags=["reorder"])

Editor = Annotated[dict, Depends(require_permission("inventory.manage"))]


@router.post("/check", response_model=list[POOut])
async def check_all_reorder(
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    """Trigger reorder check for all auto-reorder products. Returns created POs."""
    svc = ReorderService(db)
    pos = await svc.check_all_products_reorder(user["tenant_id"])
    return pos


@router.post("/check/{product_id}", response_model=POOut | None)
async def check_product_reorder(
    product_id: str,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    """Trigger reorder check for a specific product. Returns created PO or null."""
    svc = ReorderService(db)
    po = await svc.check_and_trigger_reorder(product_id, user["tenant_id"])
    return po


@router.get("/config")
async def get_reorder_config(
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    """Get reorder configuration for all auto-reorder products."""
    svc = ReorderService(db)
    return await svc.get_reorder_config(user["tenant_id"])
