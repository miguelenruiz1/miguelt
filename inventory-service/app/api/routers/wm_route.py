"""WM route / step-config endpoints (Odoo-style multi-step receive/deliver/manufacture)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.wm_route import (
    GenerateChainIn, GenerateChainResult, GeneratedOrder,
    RouteOut, RouteRuleOut, WMConfigOut, WMConfigUpdate,
)
from app.services.route_service import RouteService

router = APIRouter(prefix="/api/v1/wm", tags=["wm-routes"])


@router.get("/warehouses/{warehouse_id}/config", response_model=WMConfigOut)
async def get_config(
    warehouse_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    cfg = await RouteService(db).get_or_create_config(current_user["tenant_id"], warehouse_id)
    await db.commit()
    return ORJSONResponse(WMConfigOut.model_validate(cfg).model_dump(mode="json"))


@router.put("/warehouses/{warehouse_id}/config", response_model=WMConfigOut)
async def set_config(
    warehouse_id: str,
    body: WMConfigUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    cfg = await RouteService(db).apply_config(
        current_user["tenant_id"], warehouse_id,
        body.receive_steps, body.deliver_steps, body.manufacture_steps,
    )
    await db.commit()
    return ORJSONResponse(WMConfigOut.model_validate(cfg).model_dump(mode="json"))


@router.get("/routes", response_model=list[RouteOut])
async def list_routes(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    warehouse_id: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    pairs = await RouteService(db).list_routes(current_user["tenant_id"], warehouse_id)
    result = []
    for route, rules in pairs:
        out = RouteOut.model_validate(route)
        out.rules = [RouteRuleOut.model_validate(r) for r in rules]
        result.append(out.model_dump(mode="json"))
    return ORJSONResponse(result)


@router.post("/routes/generate-chain", response_model=GenerateChainResult, status_code=201)
async def generate_chain(
    body: GenerateChainIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    route, created = await RouteService(db).generate_chain(
        current_user["tenant_id"], body, current_user.get("id"),
    )
    await db.commit()
    result = GenerateChainResult(
        flow=route.flow, steps=route.steps,
        orders=[
            GeneratedOrder(
                id=order.id, to_number=order.to_number, sequence=rule.sequence,
                step_name=rule.name, source_zone=rule.source_zone, dest_zone=rule.dest_zone,
            )
            for rule, order in created
        ],
    )
    return ORJSONResponse(result.model_dump(mode="json"), status_code=201)
