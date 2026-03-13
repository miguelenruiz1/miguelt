"""Customer special pricing endpoints."""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.customer_price import (
    CustomerPriceCreate,
    CustomerPriceDetailOut,
    CustomerPriceHistoryOut,
    CustomerPriceMetrics,
    CustomerPriceOut,
    PriceLookupRequest,
    PriceLookupResponse,
)
from app.services.customer_price_service import CustomerPriceService
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/customer-prices", tags=["customer-prices"])

Viewer = Annotated[dict, Depends(require_permission("inventory.view"))]
PricingEditor = Annotated[dict, Depends(require_permission("inventory.manage"))]


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


@router.post("", response_model=CustomerPriceOut, status_code=201)
async def create_or_update_customer_price(
    body: CustomerPriceCreate,
    _module: ModuleUser,
    user: PricingEditor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerPriceService(db)
    audit = InventoryAuditService(db)
    cp = await svc.set_customer_price(
        tenant_id=user["tenant_id"],
        customer_id=body.customer_id,
        product_id=body.product_id,
        new_price=Decimal(str(body.price)),
        created_by=user.get("id", ""),
        created_by_name=user.get("name"),
        valid_from=body.valid_from,
        valid_to=body.valid_to,
        reason=body.reason,
        min_quantity=Decimal(str(body.min_quantity)),
        variant_id=body.variant_id,
        currency=body.currency,
    )
    # Re-fetch with eager loading
    cp = await svc.get_by_id(cp.id, user["tenant_id"])
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.customer_price.set", resource_type="customer_price",
        resource_id=cp.id,
        new_data={"customer_id": body.customer_id, "product_id": body.product_id, "price": body.price},
        ip_address=_ip(request),
    )
    return cp


@router.get("", response_model=list[CustomerPriceOut])
async def list_customer_prices(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    customer_id: str | None = None,
    product_id: str | None = None,
    is_active: bool | None = None,
    is_expired: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    svc = CustomerPriceService(db)
    return await svc.list_all(
        tenant_id=user["tenant_id"],
        customer_id=customer_id,
        product_id=product_id,
        is_active=is_active,
        is_expired=is_expired,
        offset=offset,
        limit=limit,
    )


@router.get("/metrics", response_model=CustomerPriceMetrics)
async def customer_price_metrics(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerPriceService(db)
    active = await svc.count_active(user["tenant_id"])
    expiring = await svc.count_expiring_soon(user["tenant_id"])
    customers = await svc.count_customers_with_prices(user["tenant_id"])
    return CustomerPriceMetrics(
        active_count=active,
        expiring_soon=expiring,
        customers_with_prices=customers,
    )


@router.get("/history", response_model=list[CustomerPriceHistoryOut])
async def global_price_history(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    customer_id: str | None = None,
    product_id: str | None = None,
):
    svc = CustomerPriceService(db)
    return await svc.get_history(
        tenant_id=user["tenant_id"],
        customer_id=customer_id,
        product_id=product_id,
    )


@router.post("/lookup", response_model=PriceLookupResponse)
async def price_lookup(
    body: PriceLookupRequest,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerPriceService(db)
    result = await svc.lookup(
        tenant_id=user["tenant_id"],
        customer_id=body.customer_id,
        product_id=body.product_id,
        quantity=Decimal(str(body.quantity)),
        variant_id=body.variant_id,
    )
    return PriceLookupResponse(**result)


@router.get("/{price_id}", response_model=CustomerPriceDetailOut)
async def get_customer_price_detail(
    price_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    from app.core.errors import NotFoundError
    svc = CustomerPriceService(db)
    cp = await svc.get_by_id(price_id, user["tenant_id"])
    if not cp:
        raise NotFoundError("Customer price not found")
    history = await svc.get_history(
        tenant_id=user["tenant_id"],
        customer_id=cp.customer_id,
        product_id=cp.product_id,
    )
    # Build detail response manually
    out = CustomerPriceOut.model_validate(cp).model_dump(mode="json")
    out["history"] = [CustomerPriceHistoryOut.model_validate(h).model_dump(mode="json") for h in history]
    return out


@router.delete("/{price_id}", status_code=204)
async def deactivate_customer_price(
    price_id: str,
    _module: ModuleUser,
    user: PricingEditor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerPriceService(db)
    audit = InventoryAuditService(db)
    await svc.deactivate(price_id, user["tenant_id"])
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.customer_price.deactivate", resource_type="customer_price",
        resource_id=price_id,
        ip_address=_ip(request),
    )
