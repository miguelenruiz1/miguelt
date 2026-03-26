"""Tenant configuration endpoints: all type/config CRUD."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import (
    CustomFieldCreate, CustomFieldOut, CustomFieldUpdate,
    CustomSupplierFieldCreate, CustomSupplierFieldOut, CustomSupplierFieldUpdate,
    CustomWarehouseFieldCreate, CustomWarehouseFieldOut, CustomWarehouseFieldUpdate,
    CustomMovementFieldCreate, CustomMovementFieldOut, CustomMovementFieldUpdate,
    OrderTypeCreate, OrderTypeOut, OrderTypeUpdate,
    ProductTypeCreate, ProductTypeOut, ProductTypeUpdate,
    SupplierTypeCreate, SupplierTypeOut, SupplierTypeUpdate,
    MovementTypeCreate, MovementTypeOut, MovementTypeUpdate,
    WarehouseTypeCreate, WarehouseTypeOut, WarehouseTypeUpdate,
    LocationCreate, LocationOut, LocationUpdate,
    EventTypeCreate, EventTypeOut, EventTypeUpdate,
    EventSeverityCreate, EventSeverityOut, EventSeverityUpdate,
    EventStatusCreate, EventStatusOut, EventStatusUpdate,
    SerialStatusCreate, SerialStatusOut, SerialStatusUpdate,
)
from app.services.config_service import ConfigService
from app.services.dynamic_config_service import DynamicConfigService
from app.services.audit_service import InventoryAuditService
from app.domain.schemas.pagination import (
    PaginatedMovementTypes, PaginatedWarehouseTypes, PaginatedLocations,
    PaginatedEventTypes, PaginatedEventSeverities, PaginatedEventStatuses,
    PaginatedSerialStatuses, PaginatedProductTypes, PaginatedOrderTypes,
    PaginatedCustomFields, PaginatedSupplierTypes, PaginatedCustomSupplierFields,
    PaginatedCustomWarehouseFields, PaginatedCustomMovementFields,
)

router = APIRouter(prefix="/api/v1/config", tags=["config"])


def _svc(db: AsyncSession = Depends(get_db_session)) -> ConfigService:
    return ConfigService(db)

def _dyn_svc(db: AsyncSession = Depends(get_db_session)) -> DynamicConfigService:
    return DynamicConfigService(db)

def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


# ── Movement Types ───────────────────────────────────────────────────────────

@router.get("/movement-types", response_model=PaginatedMovementTypes)
async def list_movement_types(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: DynamicConfigService = Depends(_dyn_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_movement_types(tenant_id, offset=offset, limit=limit)
    return PaginatedMovementTypes(items=items, total=total, offset=offset, limit=limit)

@router.post("/movement-types", response_model=MovementTypeOut, status_code=201)
async def create_movement_type(
    body: MovementTypeCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_movement_type(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.movement_type.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/movement-types/{type_id}", response_model=MovementTypeOut)
async def update_movement_type(
    type_id: str,
    body: MovementTypeUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_movement_type(tenant_id, type_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.movement_type.update", resource_type="config",
        resource_id=type_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/movement-types/{type_id}", status_code=204)
async def delete_movement_type(
    type_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_movement_type(tenant_id, type_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.movement_type.delete", resource_type="config",
        resource_id=type_id, ip_address=_ip(request),
    )


# ── Warehouse Types ──────────────────────────────────────────────────────────

@router.get("/warehouse-types", response_model=PaginatedWarehouseTypes)
async def list_warehouse_types(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: DynamicConfigService = Depends(_dyn_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_warehouse_types(tenant_id, offset=offset, limit=limit)
    return PaginatedWarehouseTypes(items=items, total=total, offset=offset, limit=limit)

@router.post("/warehouse-types", response_model=WarehouseTypeOut, status_code=201)
async def create_warehouse_type(
    body: WarehouseTypeCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_warehouse_type(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.warehouse_type.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/warehouse-types/{type_id}", response_model=WarehouseTypeOut)
async def update_warehouse_type(
    type_id: str,
    body: WarehouseTypeUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_warehouse_type(tenant_id, type_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.warehouse_type.update", resource_type="config",
        resource_id=type_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/warehouse-types/{type_id}", status_code=204)
async def delete_warehouse_type(
    type_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_warehouse_type(tenant_id, type_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.warehouse_type.delete", resource_type="config",
        resource_id=type_id, ip_address=_ip(request),
    )


# ── Locations ────────────────────────────────────────────────────────────────

@router.get("/locations", response_model=PaginatedLocations)
async def list_locations(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    warehouse_id: str | None = None,
    svc: DynamicConfigService = Depends(_dyn_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_locations(tenant_id, warehouse_id, offset=offset, limit=limit)
    return PaginatedLocations(items=items, total=total, offset=offset, limit=limit)

@router.post("/locations", response_model=LocationOut, status_code=201)
async def create_location(
    body: LocationCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_location(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.location.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.post("/locations/bulk", response_model=list[LocationOut], status_code=201)
async def bulk_create_locations(
    body: list[LocationCreate],
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    """Create multiple locations at once. Max 500 per request."""
    if len(body) > 500:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Max 500 locations per bulk request")
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    results = []
    for loc in body:
        result = await svc.create_location(tenant_id, loc.model_dump())
        results.append(result)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.location.bulk_create", resource_type="config",
        resource_id="bulk", new_data={"count": len(results)}, ip_address=_ip(request),
    )
    return results


@router.patch("/locations/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: str,
    body: LocationUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_location(tenant_id, location_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.location.update", resource_type="config",
        resource_id=location_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/locations/{location_id}", status_code=204)
async def delete_location(
    location_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_location(tenant_id, location_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.location.delete", resource_type="config",
        resource_id=location_id, ip_address=_ip(request),
    )


# ── Event Types ──────────────────────────────────────────────────────────────

@router.get("/event-types", response_model=PaginatedEventTypes)
async def list_event_types(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: DynamicConfigService = Depends(_dyn_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_event_types(tenant_id, offset=offset, limit=limit)
    return PaginatedEventTypes(items=items, total=total, offset=offset, limit=limit)

@router.post("/event-types", response_model=EventTypeOut, status_code=201)
async def create_event_type(
    body: EventTypeCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_event_type(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.event_type.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/event-types/{type_id}", response_model=EventTypeOut)
async def update_event_type(
    type_id: str,
    body: EventTypeUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_event_type(tenant_id, type_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.event_type.update", resource_type="config",
        resource_id=type_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/event-types/{type_id}", status_code=204)
async def delete_event_type(
    type_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_event_type(tenant_id, type_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.event_type.delete", resource_type="config",
        resource_id=type_id, ip_address=_ip(request),
    )


# ── Event Severities ────────────────────────────────────────────────────────

@router.get("/event-severities", response_model=PaginatedEventSeverities)
async def list_event_severities(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: DynamicConfigService = Depends(_dyn_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_event_severities(tenant_id, offset=offset, limit=limit)
    return PaginatedEventSeverities(items=items, total=total, offset=offset, limit=limit)

@router.post("/event-severities", response_model=EventSeverityOut, status_code=201)
async def create_event_severity(
    body: EventSeverityCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_event_severity(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.event_severity.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/event-severities/{sev_id}", response_model=EventSeverityOut)
async def update_event_severity(
    sev_id: str,
    body: EventSeverityUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_event_severity(tenant_id, sev_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.event_severity.update", resource_type="config",
        resource_id=sev_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/event-severities/{sev_id}", status_code=204)
async def delete_event_severity(
    sev_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_event_severity(tenant_id, sev_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.event_severity.delete", resource_type="config",
        resource_id=sev_id, ip_address=_ip(request),
    )


# ── Event Statuses ──────────────────────────────────────────────────────────

@router.get("/event-statuses", response_model=PaginatedEventStatuses)
async def list_event_statuses(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: DynamicConfigService = Depends(_dyn_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_event_statuses(tenant_id, offset=offset, limit=limit)
    return PaginatedEventStatuses(items=items, total=total, offset=offset, limit=limit)

@router.post("/event-statuses", response_model=EventStatusOut, status_code=201)
async def create_event_status(
    body: EventStatusCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_event_status(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.event_status.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/event-statuses/{status_id}", response_model=EventStatusOut)
async def update_event_status(
    status_id: str,
    body: EventStatusUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_event_status(tenant_id, status_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.event_status.update", resource_type="config",
        resource_id=status_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/event-statuses/{status_id}", status_code=204)
async def delete_event_status(
    status_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_event_status(tenant_id, status_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.event_status.delete", resource_type="config",
        resource_id=status_id, ip_address=_ip(request),
    )


# ── Serial Statuses ─────────────────────────────────────────────────────────

@router.get("/serial-statuses", response_model=PaginatedSerialStatuses)
async def list_serial_statuses(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: DynamicConfigService = Depends(_dyn_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_serial_statuses(tenant_id, offset=offset, limit=limit)
    return PaginatedSerialStatuses(items=items, total=total, offset=offset, limit=limit)

@router.post("/serial-statuses", response_model=SerialStatusOut, status_code=201)
async def create_serial_status(
    body: SerialStatusCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_serial_status(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.serial_status.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/serial-statuses/{status_id}", response_model=SerialStatusOut)
async def update_serial_status(
    status_id: str,
    body: SerialStatusUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_serial_status(tenant_id, status_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.serial_status.update", resource_type="config",
        resource_id=status_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/serial-statuses/{status_id}", status_code=204)
async def delete_serial_status(
    status_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: DynamicConfigService = Depends(_dyn_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_serial_status(tenant_id, status_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.serial_status.delete", resource_type="config",
        resource_id=status_id, ip_address=_ip(request),
    )


# ── Product Types ─────────────────────────────────────────────────────────────

@router.get("/product-types", response_model=PaginatedProductTypes)
async def list_product_types(
    current_user: ModuleUser, _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: ConfigService = Depends(_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_product_types(tenant_id, offset=offset, limit=limit)
    return PaginatedProductTypes(items=items, total=total, offset=offset, limit=limit)

@router.post("/product-types", response_model=ProductTypeOut, status_code=201)
async def create_product_type(
    body: ProductTypeCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_product_type(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.product_type.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/product-types/{type_id}", response_model=ProductTypeOut)
async def update_product_type(
    type_id: str,
    body: ProductTypeUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_product_type(tenant_id, type_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.product_type.update", resource_type="config",
        resource_id=type_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/product-types/{type_id}", status_code=204)
async def delete_product_type(
    type_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_product_type(tenant_id, type_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.product_type.delete", resource_type="config",
        resource_id=type_id, ip_address=_ip(request),
    )


# ── Order Types ──────────────────────────────────────────────────────────────

@router.get("/order-types", response_model=PaginatedOrderTypes)
async def list_order_types(
    current_user: ModuleUser, _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: ConfigService = Depends(_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_order_types(tenant_id, offset=offset, limit=limit)
    return PaginatedOrderTypes(items=items, total=total, offset=offset, limit=limit)

@router.post("/order-types", response_model=OrderTypeOut, status_code=201)
async def create_order_type(
    body: OrderTypeCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_order_type(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.order_type.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/order-types/{type_id}", response_model=OrderTypeOut)
async def update_order_type(
    type_id: str,
    body: OrderTypeUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_order_type(tenant_id, type_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.order_type.update", resource_type="config",
        resource_id=type_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/order-types/{type_id}", status_code=204)
async def delete_order_type(
    type_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_order_type(tenant_id, type_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.order_type.delete", resource_type="config",
        resource_id=type_id, ip_address=_ip(request),
    )


# ── Custom Fields ─────────────────────────────────────────────────────────────

@router.get("/custom-fields", response_model=PaginatedCustomFields)
async def list_custom_fields(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: ConfigService = Depends(_svc),
    product_type_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_custom_fields(tenant_id, product_type_id=product_type_id, offset=offset, limit=limit)
    return PaginatedCustomFields(items=items, total=total, offset=offset, limit=limit)

@router.post("/custom-fields", response_model=CustomFieldOut, status_code=201)
async def create_custom_field(
    body: CustomFieldCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_custom_field(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.custom_field.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/custom-fields/{field_id}", response_model=CustomFieldOut)
async def update_custom_field(
    field_id: str,
    body: CustomFieldUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_custom_field(tenant_id, field_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.custom_field.update", resource_type="config",
        resource_id=field_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/custom-fields/{field_id}", status_code=204)
async def delete_custom_field(
    field_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_custom_field(tenant_id, field_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.custom_field.delete", resource_type="config",
        resource_id=field_id, ip_address=_ip(request),
    )


# ── Supplier Types ────────────────────────────────────────────────────────────

@router.get("/supplier-types", response_model=PaginatedSupplierTypes)
async def list_supplier_types(
    current_user: ModuleUser, _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: ConfigService = Depends(_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_supplier_types(tenant_id, offset=offset, limit=limit)
    return PaginatedSupplierTypes(items=items, total=total, offset=offset, limit=limit)

@router.post("/supplier-types", response_model=SupplierTypeOut, status_code=201)
async def create_supplier_type(
    body: SupplierTypeCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_supplier_type(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.supplier_type.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/supplier-types/{type_id}", response_model=SupplierTypeOut)
async def update_supplier_type(
    type_id: str,
    body: SupplierTypeUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_supplier_type(tenant_id, type_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.supplier_type.update", resource_type="config",
        resource_id=type_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/supplier-types/{type_id}", status_code=204)
async def delete_supplier_type(
    type_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_supplier_type(tenant_id, type_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.supplier_type.delete", resource_type="config",
        resource_id=type_id, ip_address=_ip(request),
    )


# ── Custom Supplier Fields ───────────────────────────────────────────────────

@router.get("/supplier-fields", response_model=PaginatedCustomSupplierFields)
async def list_supplier_fields(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: ConfigService = Depends(_svc),
    supplier_type_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_supplier_fields(tenant_id, supplier_type_id=supplier_type_id, offset=offset, limit=limit)
    return PaginatedCustomSupplierFields(items=items, total=total, offset=offset, limit=limit)

@router.post("/supplier-fields", response_model=CustomSupplierFieldOut, status_code=201)
async def create_supplier_field(
    body: CustomSupplierFieldCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_supplier_field(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.supplier_field.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/supplier-fields/{field_id}", response_model=CustomSupplierFieldOut)
async def update_supplier_field(
    field_id: str,
    body: CustomSupplierFieldUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_supplier_field(tenant_id, field_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.supplier_field.update", resource_type="config",
        resource_id=field_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/supplier-fields/{field_id}", status_code=204)
async def delete_supplier_field(
    field_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_supplier_field(tenant_id, field_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.supplier_field.delete", resource_type="config",
        resource_id=field_id, ip_address=_ip(request),
    )


# ── Custom Warehouse Fields ─────────────────────────────────────────────────

@router.get("/warehouse-fields", response_model=PaginatedCustomWarehouseFields)
async def list_warehouse_fields(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: ConfigService = Depends(_svc),
    warehouse_type_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_warehouse_fields(tenant_id, warehouse_type_id=warehouse_type_id, offset=offset, limit=limit)
    return PaginatedCustomWarehouseFields(items=items, total=total, offset=offset, limit=limit)

@router.post("/warehouse-fields", response_model=CustomWarehouseFieldOut, status_code=201)
async def create_warehouse_field(
    body: CustomWarehouseFieldCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_warehouse_field(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.warehouse_field.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/warehouse-fields/{field_id}", response_model=CustomWarehouseFieldOut)
async def update_warehouse_field(
    field_id: str,
    body: CustomWarehouseFieldUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_warehouse_field(tenant_id, field_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.warehouse_field.update", resource_type="config",
        resource_id=field_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/warehouse-fields/{field_id}", status_code=204)
async def delete_warehouse_field(
    field_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_warehouse_field(tenant_id, field_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.warehouse_field.delete", resource_type="config",
        resource_id=field_id, ip_address=_ip(request),
    )


# ── Custom Movement Fields ──────────────────────────────────────────────────

@router.get("/movement-fields", response_model=PaginatedCustomMovementFields)
async def list_movement_fields(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    svc: ConfigService = Depends(_svc),
    movement_type_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_movement_fields(tenant_id, movement_type_id=movement_type_id, offset=offset, limit=limit)
    return PaginatedCustomMovementFields(items=items, total=total, offset=offset, limit=limit)

@router.post("/movement-fields", response_model=CustomMovementFieldOut, status_code=201)
async def create_movement_field(
    body: CustomMovementFieldCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.create_movement_field(tenant_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.movement_field.create", resource_type="config",
        resource_id=result.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.patch("/movement-fields/{field_id}", response_model=CustomMovementFieldOut)
async def update_movement_field(
    field_id: str,
    body: CustomMovementFieldUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    result = await svc.update_movement_field(tenant_id, field_id, body.model_dump())
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.movement_field.update", resource_type="config",
        resource_id=field_id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return result

@router.delete("/movement-fields/{field_id}", status_code=204)
async def delete_movement_field(
    field_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    request: Request,
    svc: ConfigService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_movement_field(tenant_id, field_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.movement_field.delete", resource_type="config",
        resource_id=field_id, ip_address=_ip(request),
    )


# ─── SO Approval Threshold ─────────────────────────────────────────────────

@router.get("/so-approval-threshold")
async def get_approval_threshold(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    from app.services.approval_service import ApprovalService
    svc = ApprovalService(db)
    tenant_id = current_user.get("tenant_id", "default")
    config = await svc.get_tenant_config(tenant_id)
    return {
        "tenant_id": tenant_id,
        "so_approval_threshold": float(config.so_approval_threshold) if config and config.so_approval_threshold is not None else None,
    }


@router.patch("/so-approval-threshold")
async def update_approval_threshold(
    body: dict,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.admin"))],
    db: AsyncSession = Depends(get_db_session),
):
    from app.services.approval_service import ApprovalService
    from decimal import Decimal
    svc = ApprovalService(db)
    tenant_id = current_user.get("tenant_id", "default")
    raw = body.get("threshold")
    threshold = Decimal(str(raw)) if raw is not None else None
    config = await svc.set_threshold(tenant_id, threshold)
    return {
        "tenant_id": tenant_id,
        "so_approval_threshold": float(config.so_approval_threshold) if config.so_approval_threshold is not None else None,
    }


# ─── Global Margin Config ─────────────────────────────────────────────────────

@router.get("/margins")
async def get_margin_config(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import select as _sel
    from app.db.models.sales_order import TenantInventoryConfig
    tenant_id = current_user.get("tenant_id", "default")
    result = await db.execute(_sel(TenantInventoryConfig).where(TenantInventoryConfig.tenant_id == tenant_id))
    config = result.scalar_one_or_none()
    if not config:
        return {
            "tenant_id": tenant_id,
            "margin_target_global": 35.0,
            "margin_minimum_global": 20.0,
            "margin_cost_method_global": "last_purchase",
        }
    return {
        "tenant_id": tenant_id,
        "margin_target_global": float(config.margin_target_global) if config.margin_target_global is not None else 35.0,
        "margin_minimum_global": float(config.margin_minimum_global) if config.margin_minimum_global is not None else 20.0,
        "margin_cost_method_global": config.margin_cost_method_global or "last_purchase",
    }


@router.patch("/margins")
async def update_margin_config(
    body: dict,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.admin"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    from decimal import Decimal
    from sqlalchemy import select as _sel
    from app.db.models.sales_order import TenantInventoryConfig
    import uuid as _uuid
    tenant_id = current_user.get("tenant_id", "default")
    result = await db.execute(_sel(TenantInventoryConfig).where(TenantInventoryConfig.tenant_id == tenant_id))
    config = result.scalar_one_or_none()
    if not config:
        config = TenantInventoryConfig(id=str(_uuid.uuid4()), tenant_id=tenant_id)
        db.add(config)
        await db.flush()
    if "margin_target_global" in body:
        config.margin_target_global = Decimal(str(body["margin_target_global"])) if body["margin_target_global"] is not None else None
    if "margin_minimum_global" in body:
        config.margin_minimum_global = Decimal(str(body["margin_minimum_global"])) if body["margin_minimum_global"] is not None else None
    if "margin_cost_method_global" in body:
        config.margin_cost_method_global = body["margin_cost_method_global"]
    await db.flush()
    audit = InventoryAuditService(db)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.config.margins.update", resource_type="config",
        resource_id=tenant_id, new_data=body, ip_address=_ip(request),
    )
    return {
        "tenant_id": tenant_id,
        "margin_target_global": float(config.margin_target_global) if config.margin_target_global is not None else 35.0,
        "margin_minimum_global": float(config.margin_minimum_global) if config.margin_minimum_global is not None else 20.0,
        "margin_cost_method_global": config.margin_cost_method_global or "last_purchase",
    }


# ─── Feature Toggles ─────────────────────────────────────────────────────────

@router.get("/features")
async def get_feature_toggles(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    """Return feature toggles for the tenant."""
    from sqlalchemy import select
    from app.db.models.sales_order import TenantInventoryConfig

    result = await db.execute(
        select(TenantInventoryConfig).where(TenantInventoryConfig.tenant_id == current_user["tenant_id"])
    )
    config = result.scalar_one_or_none()
    features = {
        "lotes": True, "seriales": True, "variantes": True, "conteo": True,
        "escaner": False, "picking": True, "eventos": True, "kardex": True,
        "precios": True, "aprobaciones": False,
    }
    if config:
        for key in features:
            val = getattr(config, f"feature_{key}", None)
            if val is not None:
                features[key] = val
    return features


@router.patch("/features")
async def update_feature_toggles(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    body: dict,
    db: AsyncSession = Depends(get_db_session),
):
    """Update feature toggles."""
    from sqlalchemy import select
    from app.db.models.sales_order import TenantInventoryConfig
    import uuid

    tenant_id = current_user["tenant_id"]
    result = await db.execute(
        select(TenantInventoryConfig).where(TenantInventoryConfig.tenant_id == tenant_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        config = TenantInventoryConfig(id=str(uuid.uuid4()), tenant_id=tenant_id)
        db.add(config)

    valid_keys = ["lotes", "seriales", "variantes", "conteo", "escaner", "picking", "eventos", "kardex", "precios", "aprobaciones"]
    for key in valid_keys:
        if key in body:
            setattr(config, f"feature_{key}", bool(body[key]))

    await db.flush()

    features = {}
    for key in valid_keys:
        features[key] = getattr(config, f"feature_{key}", True)
    return features
