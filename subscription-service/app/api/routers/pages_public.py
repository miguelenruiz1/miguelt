"""Public pages router — serves published CMS pages (no auth)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_redis
from app.db.session import get_db_session
from app.domain.cms_schemas import CmsPublicPageOut
from app.services.cms_service import CmsService

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])


async def _svc(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CmsService:
    redis = get_redis()
    return CmsService(db, redis)


@router.get("/{slug}", response_model=CmsPublicPageOut, summary="Get published page by slug (public)")
async def get_public_page(
    slug: str,
    svc: CmsService = Depends(_svc),
):
    data = await svc.get_public_page(slug)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found or not published",
        )
    return data
