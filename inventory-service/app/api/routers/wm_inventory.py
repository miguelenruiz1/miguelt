"""WM inventory endpoints: stock states, bin blocking, ERI."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.wm_inventory import (
    BinBlockIn, ERIOut, LocationStateOut, SetStockStateIn, StockStatusOut,
)
from app.services.wm_inventory_service import WMInventoryService

router = APIRouter(prefix="/api/v1/wm", tags=["wm-inventory"])


@router.post("/bins/{location_id}/block", response_model=LocationStateOut)
async def block_bin(
    location_id: str,
    body: BinBlockIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    loc = await WMInventoryService(db).block_bin(
        current_user["tenant_id"], location_id, body.blocked_inbound, body.blocked_outbound, body.block_reason,
    )
    await db.commit()
    return ORJSONResponse(LocationStateOut.model_validate(loc).model_dump(mode="json"))


@router.post("/bins/{location_id}/unblock", response_model=LocationStateOut)
async def unblock_bin(
    location_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    loc = await WMInventoryService(db).unblock_bin(current_user["tenant_id"], location_id)
    await db.commit()
    return ORJSONResponse(LocationStateOut.model_validate(loc).model_dump(mode="json"))


@router.post("/stock/{stock_level_id}/set-state")
async def set_stock_state(
    stock_level_id: str,
    body: SetStockStateIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    sl = await WMInventoryService(db).set_stock_state(current_user["tenant_id"], stock_level_id, body.stock_type)
    await db.commit()
    return ORJSONResponse({"id": sl.id, "stock_type": sl.stock_type})


@router.get("/stock-status", response_model=StockStatusOut)
async def stock_status(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    warehouse_id: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    out = await WMInventoryService(db).stock_status(current_user["tenant_id"], warehouse_id)
    return ORJSONResponse(out.model_dump(mode="json"))


@router.get("/eri", response_model=ERIOut)
async def eri(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    warehouse_id: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    out = await WMInventoryService(db).compute_eri(current_user["tenant_id"], warehouse_id)
    return ORJSONResponse(out.model_dump(mode="json"))
