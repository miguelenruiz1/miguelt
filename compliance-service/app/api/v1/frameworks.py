"""CRUD router for compliance frameworks (read-only catalogue)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.core.errors import NotFoundError
from app.db.session import get_db_session
from app.repositories.framework_repo import FrameworkRepository
from app.schemas.framework import FrameworkResponse

router = APIRouter(
    prefix="/api/v1/compliance/frameworks",
    tags=["frameworks"],
)


@router.get("/", response_model=list[FrameworkResponse])
async def list_frameworks(
    _user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
    target_market: str | None = Query(None),
    commodity: str | None = Query(None),
):
    repo = FrameworkRepository(db)
    items, _total = await repo.list(target_market=target_market, commodity=commodity)
    return items


@router.get("/{slug}", response_model=FrameworkResponse)
async def get_framework(
    slug: str,
    _user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    repo = FrameworkRepository(db)
    fw = await repo.get_by_slug(slug)
    if fw is None:
        raise NotFoundError(f"Framework '{slug}' not found")
    return fw
