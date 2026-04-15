"""Recipe (BOM) endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ProductionModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import RecipeCreate, RecipeOut, RecipeUpdate
from app.domain.schemas.pagination import PaginatedRecipes
from app.services.production_service import ProductionService
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])


from app.api.deps import get_client_ip as _ip  # noqa: F401


def _svc(db: AsyncSession = Depends(get_db_session)) -> ProductionService:
    return ProductionService(db)


@router.get("", response_model=PaginatedRecipes)
async def list_recipes(
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: ProductionService = Depends(_svc),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    tenant_id = current_user.get("tenant_id", "default")
    items, total = await svc.list_recipes(tenant_id, offset=offset, limit=limit)
    return PaginatedRecipes(items=items, total=total, offset=offset, limit=limit)


@router.post("", response_model=RecipeOut, status_code=201)
async def create_recipe(
    body: RecipeCreate,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    data = body.model_dump()
    components = [c for c in data.pop("components", [])]
    output_components = [c for c in data.pop("output_components", []) or []]
    data["created_by"] = current_user.get("id")
    recipe = await svc.create_recipe(tenant_id, data, components, output_components)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.recipe.create", resource_type="recipe",
        resource_id=recipe.id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return recipe


@router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(
    recipe_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    svc: ProductionService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    return await svc.get_recipe(tenant_id, recipe_id)


@router.patch("/{recipe_id}", response_model=RecipeOut)
async def update_recipe(
    recipe_id: str,
    body: RecipeUpdate,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    data = body.model_dump()
    components = data.pop("components", None)
    output_components = data.pop("output_components", None)
    data["updated_by"] = current_user.get("id")
    recipe = await svc.update_recipe(tenant_id, recipe_id, data, components, output_components)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.recipe.update", resource_type="recipe",
        resource_id=recipe_id, new_data=body.model_dump(mode="json"), ip_address=_ip(request),
    )
    return recipe


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    svc: ProductionService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    audit = InventoryAuditService(db)
    await svc.delete_recipe(tenant_id, recipe_id)
    await audit.log(
        tenant_id=tenant_id, user=current_user,
        action="inventory.recipe.delete", resource_type="recipe",
        resource_id=recipe_id, ip_address=_ip(request),
    )
