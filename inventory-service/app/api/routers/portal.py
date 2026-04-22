"""Customer self-service portal endpoints.

Dos modos de uso:
  1. **Portal del cliente** — el usuario tiene `customer_id` en su JWT; el
     endpoint usa ese claim. Es lo que veria un comprador externo con
     cuenta propia.
  2. **Vista admin** — un usuario con `inventory.manage` puede pasar
     `?customer_id=X` para ver el portal de cualquier cliente. Sirve para
     soporte, demos y auditoria. Sin ese permiso, el query param se ignora.

La separacion cierra el IDOR original (query param libre) sin sacrificar la
UX de "Ver Portal" desde CustomerDetailPage.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.services.portal_service import PortalService

router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


def _resolve_customer_id(current_user: dict, override: str | None) -> str:
    """Resolve the customer id for this request.

    - Admins (inventory.manage or is_superuser) pueden pasar ?customer_id=X.
    - Resto de usuarios: el customer_id sale de su JWT claim.
    - Si ninguna via da un id → 403.
    """
    is_admin = (
        current_user.get("is_superuser")
        or "inventory.manage" in (current_user.get("permissions") or [])
    )
    if override and is_admin:
        return override
    cid = current_user.get("customer_id") or current_user.get("portal_customer_id")
    if not cid:
        raise HTTPException(
            status_code=403,
            detail=(
                "Su usuario no esta vinculado a un cliente del portal. "
                "Administradores: pasen ?customer_id=<uuid>. "
                "Clientes finales: solicite al administrador la vinculacion."
            ),
        )
    return str(cid)


@router.get("/stock")
async def portal_stock(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    customer_id: str | None = Query(default=None),
) -> ORJSONResponse:
    cid = _resolve_customer_id(current_user, customer_id)
    svc = PortalService(db)
    data = await svc.get_customer_stock(current_user["tenant_id"], cid)
    return ORJSONResponse(data)


@router.get("/orders")
async def portal_orders(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    status: str | None = None,
    customer_id: str | None = Query(default=None),
) -> ORJSONResponse:
    cid = _resolve_customer_id(current_user, customer_id)
    svc = PortalService(db)
    data = await svc.get_customer_orders(
        current_user["tenant_id"], cid, status=status,
    )
    return ORJSONResponse(data)


@router.get("/orders/{order_id}")
async def portal_order_detail(
    order_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    customer_id: str | None = Query(default=None),
) -> ORJSONResponse:
    cid = _resolve_customer_id(current_user, customer_id)
    svc = PortalService(db)
    data = await svc.get_order_detail(
        current_user["tenant_id"], order_id, cid,
    )
    return ORJSONResponse(data)
