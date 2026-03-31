"""Production resources (work centers) endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ProductionModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import ProductionResourceCreate, ProductionResourceUpdate, ProductionResourceOut
from app.services.production_service import ProductionService

router = APIRouter(prefix="/api/v1/production-resources", tags=["production-resources"])


def _svc(db: AsyncSession = Depends(get_db_session)) -> ProductionService:
    return ProductionService(db)


@router.get("", response_model=list[ProductionResourceOut])
async def list_resources(
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("production.view"))],
    svc: ProductionService = Depends(_svc),
):
    return await svc.list_resources(current_user.get("tenant_id", "default"))


@router.post("", response_model=ProductionResourceOut, status_code=201)
async def create_resource(
    body: ProductionResourceCreate,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("production.manage"))],
    svc: ProductionService = Depends(_svc),
):
    return await svc.create_resource(current_user.get("tenant_id", "default"), body.model_dump())


@router.get("/{resource_id}", response_model=ProductionResourceOut)
async def get_resource(
    resource_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("production.view"))],
    svc: ProductionService = Depends(_svc),
):
    return await svc.get_resource(current_user.get("tenant_id", "default"), resource_id)


@router.patch("/{resource_id}", response_model=ProductionResourceOut)
async def update_resource(
    resource_id: str,
    body: ProductionResourceUpdate,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("production.manage"))],
    svc: ProductionService = Depends(_svc),
):
    return await svc.update_resource(current_user.get("tenant_id", "default"), resource_id, body.model_dump(exclude_none=True))


@router.delete("/{resource_id}", status_code=204)
async def delete_resource(
    resource_id: str,
    current_user: ProductionModuleUser,
    _: Annotated[dict, Depends(require_permission("production.manage"))],
    svc: ProductionService = Depends(_svc),
) -> Response:
    await svc.delete_resource(current_user.get("tenant_id", "default"), resource_id)
    return Response(status_code=204)
