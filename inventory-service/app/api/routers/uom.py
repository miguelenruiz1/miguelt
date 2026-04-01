"""UoM CRUD and conversion endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.uom import (
    UoMCreate, UoMOut, UoMConversionCreate, UoMConversionOut,
    ConvertRequest, ConvertResponse,
)
from app.services.uom_service import UoMService

router = APIRouter(prefix="/api/v1/uom", tags=["uom"])


@router.get("", response_model=list[UoMOut])
async def list_uoms(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    svc = UoMService(db)
    tenant_id = current_user["tenant_id"]
    items = await svc.list_uoms(tenant_id)
    # Auto-seed UoMs for new tenants
    if not items:
        await svc.initialize_uoms(tenant_id)
        await db.commit()
        items = await svc.list_uoms(tenant_id)
    return [UoMOut.model_validate(u) for u in items]


@router.post("/initialize", response_model=list[UoMOut])
async def initialize_uoms(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
):
    svc = UoMService(db)
    await svc.initialize_tenant_uoms(current_user["tenant_id"])
    all_uoms = await svc.list_uoms(current_user["tenant_id"])
    return [UoMOut.model_validate(u) for u in all_uoms]


@router.post("", response_model=UoMOut, status_code=201)
async def create_uom(
    body: UoMCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
):
    svc = UoMService(db)
    uom = await svc.create_uom(current_user["tenant_id"], body.model_dump())
    return UoMOut.model_validate(uom)


@router.get("/conversions", response_model=list[UoMConversionOut])
async def list_conversions(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    svc = UoMService(db)
    items = await svc.list_conversions(current_user["tenant_id"])
    return [UoMConversionOut.model_validate(c) for c in items]


@router.post("/conversions", response_model=UoMConversionOut, status_code=201)
async def create_conversion(
    body: UoMConversionCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
):
    svc = UoMService(db)
    conv = await svc.create_conversion(current_user["tenant_id"], body.model_dump())
    return UoMConversionOut.model_validate(conv)


@router.post("/convert", response_model=ConvertResponse)
async def convert_quantity(
    body: ConvertRequest,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    svc = UoMService(db)
    result = await svc.convert(body.quantity, body.from_uom, body.to_uom, current_user["tenant_id"])
    factor = await svc.get_conversion_factor(body.from_uom, body.to_uom, current_user["tenant_id"])
    return ConvertResponse(
        quantity=body.quantity,
        from_uom=body.from_uom,
        to_uom=body.to_uom,
        result=result,
        factor=factor,
    )
