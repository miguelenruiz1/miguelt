"""Product categories CRUD endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate, PaginatedCategories
from app.repositories.category_repo import CategoryRepository
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


def _build_out(cat) -> dict:
    out = CategoryOut.model_validate(cat).model_dump(mode="json")
    if cat.parent:
        out["parent_name"] = cat.parent.name
    return out


@router.get("", response_model=PaginatedCategories)
async def list_categories(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    search: str | None = None,
    is_active: bool | None = None,
    parent_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> ORJSONResponse:
    repo = CategoryRepository(db)
    items, total = await repo.list(
        tenant_id=current_user["tenant_id"],
        search=search,
        is_active=is_active,
        parent_id=parent_id,
        offset=offset,
        limit=limit,
    )
    return ORJSONResponse({
        "items": [_build_out(c) for c in items],
        "total": total,
        "offset": offset,
        "limit": limit,
    })


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(
    body: CategoryCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    repo = CategoryRepository(db)
    audit = InventoryAuditService(svc.db)
    data = body.model_dump()
    data["created_by"] = current_user.get("id")
    cat = await repo.create(current_user["tenant_id"], data)
    # Reload with parent
    cat = await repo.get_by_id(cat.id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.category.create", resource_type="category",
        resource_id=cat.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return ORJSONResponse(_build_out(cat), status_code=201)


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(
    category_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    repo = CategoryRepository(db)
    cat = await repo.get_by_id(category_id, current_user["tenant_id"])
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    return ORJSONResponse(_build_out(cat))


@router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: str,
    body: CategoryUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    repo = CategoryRepository(db)
    audit = InventoryAuditService(svc.db)
    cat = await repo.get_by_id(category_id, current_user["tenant_id"])
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    old_data = CategoryOut.model_validate(cat).model_dump(mode="json")
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_by"] = current_user.get("id")
    cat = await repo.update(cat, update_data)
    # Reload with parent
    cat = await repo.get_by_id(cat.id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.category.update", resource_type="category",
        resource_id=cat.id, old_data=old_data,
        new_data=body.model_dump(exclude_none=True), ip_address=_ip(request),
    )
    return ORJSONResponse(_build_out(cat))


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    repo = CategoryRepository(db)
    audit = InventoryAuditService(svc.db)
    cat = await repo.get_by_id(category_id, current_user["tenant_id"])
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    await repo.delete(cat)
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.category.delete", resource_type="category",
        resource_id=category_id, ip_address=_ip(request),
    )
    await svc.db.commit()
    return Response(status_code=204)
