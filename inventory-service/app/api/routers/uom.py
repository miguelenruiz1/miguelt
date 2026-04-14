"""UoM CRUD and conversion endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.uom import (
    UoMCreate, UoMOut, UoMConversionCreate, UoMConversionOut,
    ConvertRequest, ConvertResponse,
    SetupRequest, SetupResponse, ChangeBaseRequest, ChangeBaseResponse,
    StandardCategory,
)
from app.services.uom_service import UoMService, _STANDARD_UOMS

router = APIRouter(prefix="/api/v1/uom", tags=["uom"])


@router.get("", response_model=list[UoMOut])
async def list_uoms(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    svc = UoMService(db)
    items = await svc.list_uoms(current_user["tenant_id"])
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


_CATEGORY_LABELS = {
    "weight": "Peso",
    "volume": "Volumen",
    "length": "Longitud",
    "area": "Área",
    "unit": "Cantidad",
    "time": "Tiempo",
    "energy": "Energía",
    "custom": "Personalizado",
}


@router.get("/catalog", response_model=list[StandardCategory])
async def get_setup_catalog(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
):
    """Returns the standard UoMs grouped by category, for the setup wizard."""
    by_cat: dict[str, list[dict]] = {}
    for name, symbol, category, is_implicit_base, _factor in _STANDARD_UOMS:
        by_cat.setdefault(category, []).append({
            "symbol": symbol,
            "name": name,
            "suggested_default": bool(is_implicit_base),
        })
    return [
        StandardCategory(category=cat, label=_CATEGORY_LABELS.get(cat, cat), options=opts)
        for cat, opts in by_cat.items()
    ]


@router.post("/setup", response_model=SetupResponse, status_code=201)
async def setup_uoms(
    body: SetupRequest,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
):
    """First-time setup wizard — chooses base UoM per category."""
    svc = UoMService(db)
    bases_dict = [b.model_dump() for b in body.bases]
    result = await svc.setup_tenant_uoms(current_user["tenant_id"], bases_dict)
    return SetupResponse(**result)


@router.delete("/categories/{category}", status_code=204)
async def delete_category(
    category: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
):
    """Soft-delete every UoM and conversion of a whole category.
    Blocked with 409 if any UoM in the category is in use."""
    svc = UoMService(db)
    ok, blocking = await svc.delete_category(current_user["tenant_id"], category)
    if not ok and not blocking:
        raise HTTPException(status_code=404, detail="Categoría sin unidades activas")
    if not ok:
        parts = []
        for entry in blocking:
            areas = ", ".join(f"{u['area']} ({u['count']})" for u in entry["usage"])
            parts.append(f"{entry['uom']}: {areas}")
        raise HTTPException(
            status_code=409,
            detail={
                "message": "No se puede eliminar la categoría: hay unidades en uso. " + " · ".join(parts),
                "blocking": blocking,
            },
        )
    return None


@router.post("/categories/{category}/change-base", response_model=ChangeBaseResponse)
async def change_category_base(
    category: str,
    body: ChangeBaseRequest,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.admin"))],
    db: AsyncSession = Depends(get_db_session),
):
    """Admin operation: change the base UoM of a category. Recalculates
    all qty_in_base_uom in transactional tables. Atomic."""
    svc = UoMService(db)
    result = await svc.change_category_base(current_user["tenant_id"], category, body.new_base_id)
    return ChangeBaseResponse(**result)


@router.delete("/conversions/{conversion_id}", status_code=204)
async def delete_conversion(
    conversion_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
):
    svc = UoMService(db)
    ok = await svc.delete_conversion(current_user["tenant_id"], conversion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversión no encontrada")
    return None


@router.delete("/{uom_id}", status_code=204)
async def delete_uom(
    uom_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
):
    svc = UoMService(db)
    ok, usage = await svc.delete_uom(current_user["tenant_id"], uom_id)
    if not ok and not usage:
        raise HTTPException(status_code=404, detail="UoM no encontrada")
    if not ok:
        parts = ", ".join(f"{u['area']} ({u['count']})" for u in usage)
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"No se puede eliminar: está en uso en {parts}",
                "usage": usage,
            },
        )
    return None


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
