"""Tax categories CRUD endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.tax import (
    TaxCategoryCreate, TaxCategoryUpdate, TaxCategoryOut,
)
from app.services.tax_category_service import TaxCategoryService

router = APIRouter(prefix="/api/v1/tax-categories", tags=["tax-categories"])

Viewer = Annotated[dict, Depends(require_permission("inventory.view"))]
Editor = Annotated[dict, Depends(require_permission("inventory.manage"))]


@router.get("", response_model=list[TaxCategoryOut])
async def list_categories(
    current_user: ModuleUser,
    _: Viewer,
    db: AsyncSession = Depends(get_db_session),
    include_inactive: bool = False,
):
    svc = TaxCategoryService(db)
    rows = await svc.list_categories(current_user["tenant_id"], include_inactive=include_inactive)
    out = []
    for cat, count in rows:
        item = TaxCategoryOut.model_validate(cat)
        item.rate_count = count
        out.append(item)
    return out


@router.post("", response_model=TaxCategoryOut, status_code=201)
async def create_category(
    body: TaxCategoryCreate,
    current_user: ModuleUser,
    _: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = TaxCategoryService(db)
    cat = await svc.create_category(current_user["tenant_id"], body.model_dump())
    out = TaxCategoryOut.model_validate(cat)
    out.rate_count = 0
    return out


@router.patch("/{category_id}", response_model=TaxCategoryOut)
async def update_category(
    category_id: str,
    body: TaxCategoryUpdate,
    current_user: ModuleUser,
    _: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = TaxCategoryService(db)
    cat = await svc.update_category(
        current_user["tenant_id"], category_id, body.model_dump(exclude_none=True)
    )
    return TaxCategoryOut.model_validate(cat)


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    current_user: ModuleUser,
    _: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = TaxCategoryService(db)
    ok, rate_count = await svc.delete_category(current_user["tenant_id"], category_id)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"No se puede eliminar: hay {rate_count} tarifa(s) activa(s) en esta categoría.",
                "rate_count": rate_count,
            },
        )
    return None
