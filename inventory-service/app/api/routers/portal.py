"""Customer self-service portal endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.services.portal_service import PortalService

router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


@router.get("/stock")
async def portal_stock(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    customer_id: str = Query(..., description="Customer ID to scope stock query"),
) -> ORJSONResponse:
    svc = PortalService(db)
    data = await svc.get_customer_stock(current_user["tenant_id"], customer_id)
    return ORJSONResponse(data)


@router.get("/orders")
async def portal_orders(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    customer_id: str = Query(..., description="Customer ID"),
    status: str | None = None,
) -> ORJSONResponse:
    svc = PortalService(db)
    data = await svc.get_customer_orders(
        current_user["tenant_id"], customer_id, status=status,
    )
    return ORJSONResponse(data)


@router.get("/orders/{order_id}")
async def portal_order_detail(
    order_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    customer_id: str = Query(..., description="Customer ID"),
) -> ORJSONResponse:
    svc = PortalService(db)
    data = await svc.get_order_detail(
        current_user["tenant_id"], order_id, customer_id,
    )
    return ORJSONResponse(data)
