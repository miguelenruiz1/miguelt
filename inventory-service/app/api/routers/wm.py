"""Warehouse-Management (WM) endpoints — storage types, sections, bulk bins.

All under /api/v1/wm so the gateway needs a single route. The classic
location CRUD stays where it is; this router adds the WM structural layer.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, get_client_ip as _ip, require_permission
from app.core.errors import ConflictError, NotFoundError
from app.db.session import get_db_session
from app.domain.schemas.wm import (
    BinBulkCreate, BinBulkResult, EmptyBinReport,
    StorageSectionCreate, StorageSectionOut, StorageSectionUpdate,
    StorageTypeCreate, StorageTypeOut, StorageTypeUpdate,
)
from app.repositories.wm_repo import StorageSectionRepository, StorageTypeRepository
from app.services.audit_service import InventoryAuditService
from app.services.wm_service import WMService

router = APIRouter(prefix="/api/v1/wm", tags=["wm"])


# ─── Storage Types ────────────────────────────────────────────────────────────

@router.get("/storage-types", response_model=list[StorageTypeOut])
async def list_storage_types(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    warehouse_id: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    repo = StorageTypeRepository(db)
    items = await repo.list(current_user["tenant_id"], warehouse_id=warehouse_id, is_active=is_active)
    return ORJSONResponse([StorageTypeOut.model_validate(i).model_dump(mode="json", by_alias=True) for i in items])


@router.post("/storage-types", response_model=StorageTypeOut, status_code=201)
async def create_storage_type(
    body: StorageTypeCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    tenant_id = current_user["tenant_id"]
    repo = StorageTypeRepository(db)
    if await repo.get_by_code(tenant_id, body.warehouse_id, body.code):
        raise ConflictError(f"Storage type {body.code!r} already exists in this warehouse")
    data = body.model_dump(by_alias=False)
    data["created_by"] = current_user.get("id")
    obj = await repo.create(tenant_id, data)
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user, action="inventory.wm.storage_type.create",
        resource_type="wm_storage_type", resource_id=obj.id, new_data=body.model_dump(mode="json"),
        ip_address=_ip(request),
    )
    await db.commit()
    return ORJSONResponse(StorageTypeOut.model_validate(obj).model_dump(mode="json", by_alias=True), status_code=201)


@router.patch("/storage-types/{type_id}", response_model=StorageTypeOut)
async def update_storage_type(
    type_id: str,
    body: StorageTypeUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    repo = StorageTypeRepository(db)
    obj = await repo.get(current_user["tenant_id"], type_id)
    if not obj:
        raise NotFoundError(f"Storage type {type_id!r} not found")
    obj = await repo.update(obj, body.model_dump(exclude_none=True, by_alias=False))
    await db.commit()
    return ORJSONResponse(StorageTypeOut.model_validate(obj).model_dump(mode="json", by_alias=True))


@router.delete("/storage-types/{type_id}", status_code=204)
async def delete_storage_type(
    type_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    repo = StorageTypeRepository(db)
    obj = await repo.get(current_user["tenant_id"], type_id)
    if not obj:
        raise NotFoundError(f"Storage type {type_id!r} not found")
    await repo.delete(obj)
    await db.commit()
    return Response(status_code=204)


# ─── Storage Sections ─────────────────────────────────────────────────────────

@router.get("/storage-sections", response_model=list[StorageSectionOut])
async def list_storage_sections(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    storage_type_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    repo = StorageSectionRepository(db)
    items = await repo.list(current_user["tenant_id"], storage_type_id=storage_type_id)
    return ORJSONResponse([StorageSectionOut.model_validate(i).model_dump(mode="json") for i in items])


@router.post("/storage-sections", response_model=StorageSectionOut, status_code=201)
async def create_storage_section(
    body: StorageSectionCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    tenant_id = current_user["tenant_id"]
    repo = StorageSectionRepository(db)
    if await repo.get_by_code(tenant_id, body.storage_type_id, body.code):
        raise ConflictError(f"Storage section {body.code!r} already exists in this type")
    obj = await repo.create(tenant_id, body.model_dump())
    await db.commit()
    return ORJSONResponse(StorageSectionOut.model_validate(obj).model_dump(mode="json"), status_code=201)


@router.patch("/storage-sections/{section_id}", response_model=StorageSectionOut)
async def update_storage_section(
    section_id: str,
    body: StorageSectionUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    repo = StorageSectionRepository(db)
    obj = await repo.get(current_user["tenant_id"], section_id)
    if not obj:
        raise NotFoundError(f"Storage section {section_id!r} not found")
    obj = await repo.update(obj, body.model_dump(exclude_none=True))
    await db.commit()
    return ORJSONResponse(StorageSectionOut.model_validate(obj).model_dump(mode="json"))


@router.delete("/storage-sections/{section_id}", status_code=204)
async def delete_storage_section(
    section_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    repo = StorageSectionRepository(db)
    obj = await repo.get(current_user["tenant_id"], section_id)
    if not obj:
        raise NotFoundError(f"Storage section {section_id!r} not found")
    await repo.delete(obj)
    await db.commit()
    return Response(status_code=204)


# ─── Bulk bins (SAP LS10) + empty-bin report ──────────────────────────────────

@router.post("/bins/bulk", response_model=BinBulkResult, status_code=201)
async def bulk_create_bins(
    body: BinBulkCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    tenant_id = current_user["tenant_id"]
    result = await WMService(db).bulk_create_bins(tenant_id, body, current_user.get("id"))
    await InventoryAuditService(db).log(
        tenant_id=tenant_id, user=current_user, action="inventory.wm.bins.bulk_create",
        resource_type="warehouse_location", resource_id=body.warehouse_id,
        new_data={"created": result.created, "skipped": result.skipped}, ip_address=_ip(request),
    )
    await db.commit()
    return ORJSONResponse(result.model_dump(mode="json"), status_code=201)


@router.get("/bins/empty-report", response_model=EmptyBinReport)
async def empty_bin_report(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    warehouse_id: str = Query(...),
    storage_type_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    report = await WMService(db).empty_bin_report(
        current_user["tenant_id"], warehouse_id, storage_type_id=storage_type_id,
    )
    return ORJSONResponse(report.model_dump(mode="json"))
