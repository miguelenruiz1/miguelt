"""Customer self-service portal endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.services.portal_service import PortalService

router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


def _bound_customer_id(current_user: dict) -> str:
    """Resolve the customer the caller is authorized to act as.

    The portal is a customer-facing surface: clients used to pass `customer_id`
    as a query string, which made every endpoint an IDOR (any logged-in user
    could read any other customer's stock and orders). The customer must come
    from the authenticated subject — either a `customer_id` claim on the JWT
    or the corresponding field on the cached "me" payload. Superusers may pass
    `customer_id` explicitly via a separate admin endpoint, not this one.
    """
    cid = current_user.get("customer_id") or current_user.get("portal_customer_id")
    if not cid:
        raise HTTPException(
            status_code=403,
            detail=(
                "Su usuario no esta vinculado a un cliente del portal. "
                "Solicite al administrador la vinculacion."
            ),
        )
    return str(cid)


@router.get("/stock")
async def portal_stock(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    customer_id = _bound_customer_id(current_user)
    svc = PortalService(db)
    data = await svc.get_customer_stock(current_user["tenant_id"], customer_id)
    return ORJSONResponse(data)


@router.get("/orders")
async def portal_orders(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    status: str | None = None,
) -> ORJSONResponse:
    customer_id = _bound_customer_id(current_user)
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
) -> ORJSONResponse:
    customer_id = _bound_customer_id(current_user)
    svc = PortalService(db)
    data = await svc.get_order_detail(
        current_user["tenant_id"], order_id, customer_id,
    )
    return ORJSONResponse(data)
