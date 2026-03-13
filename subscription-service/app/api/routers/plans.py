"""Plans router.

Read endpoints use permission-based auth (any tenant admin can view plans).
Write endpoints are superuser-only (plans are global, managed by Trace operators).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas import PlanCreate, PlanResponse, PlanUpdate
from app.services.plan_service import PlanService

router = APIRouter(prefix="/api/v1/plans", tags=["plans"])


def _require_superuser(current_user: CurrentUser) -> dict:
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user


SuperUser = Annotated[dict, Depends(_require_superuser)]


def _svc(db: Annotated[AsyncSession, Depends(get_db_session)]) -> PlanService:
    return PlanService(db)


@router.get("/", response_model=list[PlanResponse])
async def list_plans(
    _: Annotated[dict, Depends(require_permission("subscription.view"))],
    include_archived: bool = Query(default=False),
    svc: PlanService = Depends(_svc),
):
    return await svc.list_plans(include_archived=include_archived)


@router.post("/", response_model=PlanResponse, status_code=201)
async def create_plan(
    body: PlanCreate,
    _: SuperUser,
    svc: PlanService = Depends(_svc),
):
    return await svc.create_plan(body.model_dump())


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    _: Annotated[dict, Depends(require_permission("subscription.view"))],
    svc: PlanService = Depends(_svc),
):
    return await svc.get_plan(plan_id)


@router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    body: PlanUpdate,
    _: SuperUser,
    svc: PlanService = Depends(_svc),
):
    return await svc.update_plan(plan_id, body.model_dump(exclude_none=True))


@router.delete("/{plan_id}", status_code=204)
async def archive_plan(
    plan_id: str,
    _: SuperUser,
    svc: PlanService = Depends(_svc),
):
    await svc.archive_plan(plan_id)
