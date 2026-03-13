"""Product variant and variant attribute endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.variant import (
    PaginatedVariants, ProductVariantCreate, ProductVariantOut, ProductVariantUpdate,
    VariantAttributeCreate, VariantAttributeOut, VariantAttributeUpdate,
    VariantOptionIn, VariantOptionOut,
)
from app.services.variant_service import VariantService

router = APIRouter(prefix="/api/v1", tags=["variants"])

Viewer = Annotated[dict, Depends(require_permission("inventory.view"))]
Editor = Annotated[dict, Depends(require_permission("inventory.manage"))]


# ── Variant Attributes ──────────────────────────────────────────────
@router.get("/variant-attributes", response_model=list[VariantAttributeOut])
async def list_variant_attributes(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    return await svc.list_attributes(user["tenant_id"])


@router.post("/variant-attributes", response_model=VariantAttributeOut, status_code=201)
async def create_variant_attribute(
    body: VariantAttributeCreate,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    data = body.model_dump(exclude={"options"})
    options = [o.model_dump() for o in body.options] if body.options else None
    return await svc.create_attribute(user["tenant_id"], data, options)


@router.patch("/variant-attributes/{attr_id}", response_model=VariantAttributeOut)
async def update_variant_attribute(
    attr_id: str,
    body: VariantAttributeUpdate,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    return await svc.update_attribute(attr_id, user["tenant_id"], body.model_dump(exclude_unset=True))


@router.delete("/variant-attributes/{attr_id}", status_code=204)
async def delete_variant_attribute(
    attr_id: str,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    await svc.delete_attribute(attr_id, user["tenant_id"])


# ── Attribute Options ───────────────────────────────────────────────
@router.post("/variant-attributes/{attr_id}/options", response_model=VariantOptionOut, status_code=201)
async def add_option(
    attr_id: str,
    body: VariantOptionIn,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    return await svc.add_option(attr_id, user["tenant_id"], body.model_dump())


@router.patch("/variant-options/{option_id}", response_model=VariantOptionOut)
async def update_option(
    option_id: str,
    body: VariantOptionIn,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    return await svc.update_option(option_id, body.model_dump(exclude_unset=True), user["tenant_id"])


@router.delete("/variant-options/{option_id}", status_code=204)
async def delete_option(
    option_id: str,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    await svc.delete_option(option_id, user["tenant_id"])


# ── Product Variants ────────────────────────────────────────────────
@router.get("/variants", response_model=PaginatedVariants)
async def list_variants(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    parent_id: str | None = None,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    svc = VariantService(db)
    items, total = await svc.list_variants(user["tenant_id"], parent_id=parent_id, search=search, offset=offset, limit=limit)
    return PaginatedVariants(items=items, total=total, offset=offset, limit=limit)


@router.get("/products/{product_id}/variants", response_model=list[ProductVariantOut])
async def list_product_variants(
    product_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    return await svc.list_variants_for_product(product_id, user["tenant_id"])


@router.get("/variants/{variant_id}", response_model=ProductVariantOut)
async def get_variant(
    variant_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    return await svc.get_variant(variant_id, user["tenant_id"])


@router.post("/variants", response_model=ProductVariantOut, status_code=201)
async def create_variant(
    body: ProductVariantCreate,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    return await svc.create_variant(user["tenant_id"], body.model_dump())


@router.patch("/variants/{variant_id}", response_model=ProductVariantOut)
async def update_variant(
    variant_id: str,
    body: ProductVariantUpdate,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    return await svc.update_variant(variant_id, user["tenant_id"], body.model_dump(exclude_unset=True))


@router.delete("/variants/{variant_id}", status_code=204)
async def delete_variant(
    variant_id: str,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    svc = VariantService(db)
    await svc.delete_variant(variant_id, user["tenant_id"])
