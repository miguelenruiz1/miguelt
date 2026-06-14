"""WM putaway / removal / packaging endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import ORJSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.core.errors import NotFoundError
from app.db.models import PackageType, PutawayRule
from app.db.session import get_db_session
from app.domain.schemas.wm_putaway import (
    PackageTypeCreate, PackageTypeOut, PutawayProposeIn, PutawayProposeOut,
    PutawayRuleCreate, PutawayRuleOut, RemovalPlanIn, RemovalPlanOut,
)
from app.services.putaway_service import PutawayService

router = APIRouter(prefix="/api/v1/wm", tags=["wm-putaway"])


# ─── Putaway rules ────────────────────────────────────────────────────────────

@router.get("/putaway-rules", response_model=list[PutawayRuleOut])
async def list_putaway_rules(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    warehouse_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    q = select(PutawayRule).where(PutawayRule.tenant_id == current_user["tenant_id"])
    if warehouse_id:
        q = q.where(PutawayRule.warehouse_id == warehouse_id)
    rows = list((await db.execute(q.order_by(PutawayRule.priority))).scalars().all())
    return ORJSONResponse([PutawayRuleOut.model_validate(r).model_dump(mode="json") for r in rows])


@router.post("/putaway-rules", response_model=PutawayRuleOut, status_code=201)
async def create_putaway_rule(
    body: PutawayRuleCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    obj = PutawayRule(id=str(uuid.uuid4()), tenant_id=current_user["tenant_id"], **body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return ORJSONResponse(PutawayRuleOut.model_validate(obj).model_dump(mode="json"), status_code=201)


@router.delete("/putaway-rules/{rule_id}", status_code=204)
async def delete_putaway_rule(
    rule_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    obj = (await db.execute(
        select(PutawayRule).where(
            PutawayRule.tenant_id == current_user["tenant_id"], PutawayRule.id == rule_id,
        )
    )).scalar_one_or_none()
    if not obj:
        raise NotFoundError(f"Putaway rule {rule_id!r} not found")
    await db.delete(obj)
    await db.commit()
    return Response(status_code=204)


# ─── Package types ────────────────────────────────────────────────────────────

@router.get("/package-types", response_model=list[PackageTypeOut])
async def list_package_types(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    rows = list((await db.execute(
        select(PackageType).where(PackageType.tenant_id == current_user["tenant_id"]).order_by(PackageType.code)
    )).scalars().all())
    return ORJSONResponse([PackageTypeOut.model_validate(r).model_dump(mode="json") for r in rows])


@router.post("/package-types", response_model=PackageTypeOut, status_code=201)
async def create_package_type(
    body: PackageTypeCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    obj = PackageType(id=str(uuid.uuid4()), tenant_id=current_user["tenant_id"], **body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return ORJSONResponse(PackageTypeOut.model_validate(obj).model_dump(mode="json"), status_code=201)


# ─── Putaway proposal + removal plan ──────────────────────────────────────────

@router.post("/putaway/propose", response_model=PutawayProposeOut)
async def propose_putaway(
    body: PutawayProposeIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    out = await PutawayService(db).propose(
        current_user["tenant_id"], body.warehouse_id, body.product_id, body.quantity,
    )
    return ORJSONResponse(out.model_dump(mode="json"))


@router.post("/removal/plan", response_model=RemovalPlanOut)
async def removal_plan(
    body: RemovalPlanIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    out = await PutawayService(db).removal_plan(
        current_user["tenant_id"], body.warehouse_id, body.product_id, body.quantity, body.strategy,
    )
    return ORJSONResponse(out.model_dump(mode="json"))
