"""WM material-master endpoints (per product × warehouse WM attributes)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.models import ProductWarehouseData
from app.db.session import get_db_session
from app.domain.schemas.wm_material import ProductWMDataIn, ProductWMDataOut

router = APIRouter(prefix="/api/v1/wm", tags=["wm-material"])


async def _get(db: AsyncSession, tenant_id: str, product_id: str, warehouse_id: str) -> ProductWarehouseData | None:
    return (await db.execute(
        select(ProductWarehouseData).where(
            ProductWarehouseData.tenant_id == tenant_id,
            ProductWarehouseData.product_id == product_id,
            ProductWarehouseData.warehouse_id == warehouse_id,
        )
    )).scalar_one_or_none()


@router.get("/product-wm-data", response_model=ProductWMDataOut | None)
async def get_product_wm_data(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    product_id: str = Query(...),
    warehouse_id: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    obj = await _get(db, current_user["tenant_id"], product_id, warehouse_id)
    if not obj:
        return ORJSONResponse(None)
    return ORJSONResponse(ProductWMDataOut.model_validate(obj).model_dump(mode="json"))


@router.put("/product-wm-data", response_model=ProductWMDataOut)
async def upsert_product_wm_data(
    body: ProductWMDataIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    product_id: str = Query(...),
    warehouse_id: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    tenant_id = current_user["tenant_id"]
    obj = await _get(db, tenant_id, product_id, warehouse_id)
    data = body.model_dump()
    if obj is None:
        obj = ProductWarehouseData(
            id=str(uuid.uuid4()), tenant_id=tenant_id,
            product_id=product_id, warehouse_id=warehouse_id, **data,
        )
        db.add(obj)
    else:
        for k, v in data.items():
            setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return ORJSONResponse(ProductWMDataOut.model_validate(obj).model_dump(mode="json"))
