"""Tax rates CRUD endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.tax import TaxRateCreate, TaxRateOut, TaxRateUpdate, TaxRateSummary
from app.services.tax_service import TaxService

router = APIRouter(prefix="/api/v1/tax-rates", tags=["tax-rates"])

Viewer = Annotated[dict, Depends(require_permission("inventory.view"))]
Editor = Annotated[dict, Depends(require_permission("inventory.manage"))]


@router.get("", response_model=list[TaxRateOut])
async def list_tax_rates(
    current_user: ModuleUser,
    _: Viewer,
    db: AsyncSession = Depends(get_db_session),
    tax_type: str | None = None,
    category_id: str | None = None,
    is_active: bool | None = True,
) -> ORJSONResponse:
    svc = TaxService(db)
    rates = await svc.list_rates(
        current_user["tenant_id"],
        tax_type=tax_type,
        category_id=category_id,
        is_active=is_active,
    )
    return ORJSONResponse([TaxRateOut.model_validate(r).model_dump(mode="json") for r in rates])


@router.get("/summary", response_model=TaxRateSummary)
async def get_tax_summary(
    current_user: ModuleUser,
    _: Viewer,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = TaxService(db)
    summary = await svc.get_summary(current_user["tenant_id"])
    return ORJSONResponse({
        "default_iva": TaxRateOut.model_validate(summary["default_iva"]).model_dump(mode="json") if summary["default_iva"] else None,
        "available_iva": [TaxRateOut.model_validate(r).model_dump(mode="json") for r in summary["available_iva"]],
        "available_retention": [TaxRateOut.model_validate(r).model_dump(mode="json") for r in summary["available_retention"]],
    })


@router.post("", response_model=TaxRateOut, status_code=201)
async def create_tax_rate(
    body: TaxRateCreate,
    current_user: ModuleUser,
    _: Editor,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = TaxService(db)
    rate = await svc.create_rate(current_user["tenant_id"], body.model_dump())
    return ORJSONResponse(TaxRateOut.model_validate(rate).model_dump(mode="json"), status_code=201)


@router.patch("/{rate_id}", response_model=TaxRateOut)
async def update_tax_rate(
    rate_id: str,
    body: TaxRateUpdate,
    current_user: ModuleUser,
    _: Editor,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = TaxService(db)
    rate = await svc.update_rate(rate_id, current_user["tenant_id"], body.model_dump(exclude_none=True))
    return ORJSONResponse(TaxRateOut.model_validate(rate).model_dump(mode="json"))


@router.delete("/{rate_id}", response_model=TaxRateOut)
async def deactivate_tax_rate(
    rate_id: str,
    current_user: ModuleUser,
    _: Editor,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = TaxService(db)
    rate = await svc.deactivate_rate(rate_id, current_user["tenant_id"])
    return ORJSONResponse(TaxRateOut.model_validate(rate).model_dump(mode="json"))


@router.post("/initialize", response_model=list[TaxRateOut])
async def initialize_tax_rates(
    current_user: ModuleUser,
    _: Editor,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = TaxService(db)
    created = await svc.initialize_tenant_rates(current_user["tenant_id"])
    return ORJSONResponse([TaxRateOut.model_validate(r).model_dump(mode="json") for r in created])
