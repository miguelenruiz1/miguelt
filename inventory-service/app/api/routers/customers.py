"""Customers and customer types endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.customer import (
    CustomerCreate, CustomerOut, CustomerTypeCreate, CustomerTypeOut, CustomerTypeUpdate,
    CustomerUpdate, PaginatedCustomers,
)
from app.domain.schemas.pagination import PaginatedCustomerTypes
from app.services.customer_service import CustomerService
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1", tags=["customers"])

Viewer = Annotated[dict, Depends(require_permission("inventory.view"))]
Editor = Annotated[dict, Depends(require_permission("inventory.manage"))]


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


# ── Customer Types ──────────────────────────────────────────────────
@router.get("/config/customer-types", response_model=PaginatedCustomerTypes)
async def list_customer_types(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    svc = CustomerService(db)
    items, total = await svc.list_types(user["tenant_id"], offset=offset, limit=limit)
    return PaginatedCustomerTypes(items=items, total=total, offset=offset, limit=limit)


@router.post("/config/customer-types", response_model=CustomerTypeOut, status_code=201)
async def create_customer_type(
    body: CustomerTypeCreate,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerService(db)
    audit = InventoryAuditService(db)
    ct = await svc.create_type(user["tenant_id"], body.model_dump())
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.customer_type.create", resource_type="customer_type",
        resource_id=ct.id,
        new_data={"name": ct.name},
        ip_address=_ip(request),
    )
    return ct


@router.patch("/config/customer-types/{type_id}", response_model=CustomerTypeOut)
async def update_customer_type(
    type_id: str,
    body: CustomerTypeUpdate,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerService(db)
    audit = InventoryAuditService(db)
    result = await svc.update_type(type_id, user["tenant_id"], body.model_dump(exclude_unset=True))
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.customer_type.update", resource_type="customer_type",
        resource_id=type_id,
        new_data={"name": result.name, **body.model_dump(exclude_unset=True)},
        ip_address=_ip(request),
    )
    return result


@router.delete("/config/customer-types/{type_id}", status_code=204)
async def delete_customer_type(
    type_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerService(db)
    audit = InventoryAuditService(db)
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.customer_type.delete", resource_type="customer_type",
        resource_id=type_id,
        ip_address=_ip(request),
    )
    await db.commit()
    await svc.delete_type(type_id, user["tenant_id"])


# ── Customers ───────────────────────────────────────────────────────
@router.get("/customers", response_model=PaginatedCustomers)
async def list_customers(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    customer_type_id: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    svc = CustomerService(db)
    items, total = await svc.list_customers(
        user["tenant_id"],
        customer_type_id=customer_type_id,
        is_active=is_active,
        search=search,
        offset=offset,
        limit=limit,
    )
    return PaginatedCustomers(items=items, total=total, offset=offset, limit=limit)


@router.get("/customers/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerService(db)
    return await svc.get_customer(customer_id, user["tenant_id"])


@router.post("/customers", response_model=CustomerOut, status_code=201)
async def create_customer(
    body: CustomerCreate,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerService(db)
    audit = InventoryAuditService(db)
    data = body.model_dump()
    data["created_by"] = user.get("id")
    customer = await svc.create_customer(user["tenant_id"], data)
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.customer.create", resource_type="customer",
        resource_id=customer.id,
        new_data={"name": customer.name, "email": getattr(customer, "email", None), "phone": getattr(customer, "phone", None)},
        ip_address=_ip(request),
    )
    return customer


@router.patch("/customers/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerService(db)
    audit = InventoryAuditService(db)
    data = body.model_dump(exclude_unset=True)
    data["updated_by"] = user.get("id")
    result = await svc.update_customer(customer_id, user["tenant_id"], data)
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.customer.update", resource_type="customer",
        resource_id=customer_id,
        new_data={"name": result.name, **body.model_dump(exclude_unset=True)},
        ip_address=_ip(request),
    )
    return result


@router.delete("/customers/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = CustomerService(db)
    audit = InventoryAuditService(db)
    customer = await svc.get_customer(customer_id, user["tenant_id"])
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.customer.delete", resource_type="customer",
        resource_id=customer_id,
        old_data={"name": customer.name},
        ip_address=_ip(request),
    )
    await db.commit()
    await svc.delete_customer(customer_id, user["tenant_id"])


# ── Customer Special Prices ────────────────────────────────────────
@router.get("/customers/{customer_id}/special-prices")
async def get_customer_special_prices(
    customer_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    """Return all active special/negotiated prices for a customer."""
    from app.services.customer_price_service import CustomerPriceService
    from app.domain.schemas.customer_price import CustomerPriceOut
    svc = CustomerPriceService(db)
    prices = await svc.list_for_customer(user["tenant_id"], customer_id, active_only=True)
    return [CustomerPriceOut.model_validate(p) for p in prices]
