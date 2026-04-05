"""CMS admin router — page builder management (superuser only)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_redis
from app.db.session import get_db_session
from app.domain.cms_schemas import (
    CmsPageCreate, CmsPageOut, CmsPageUpdate,
    CmsSectionCreate, CmsSectionOut, CmsSectionUpdate,
    CmsScriptCreate, CmsScriptOut, CmsScriptUpdate,
    ReorderRequest,
)
from app.services.cms_service import CmsService

router = APIRouter(prefix="/api/v1/cms", tags=["cms"])


# ─── Dependencies ─────────────────────────────────────────────────────────────

def _require_superuser(current_user: CurrentUser) -> dict:
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los operadores de la plataforma pueden gestionar el CMS.",
        )
    return current_user


SuperuserDep = Annotated[dict, Depends(_require_superuser)]


async def _svc(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CmsService:
    redis = get_redis()
    return CmsService(db, redis)


# ─── Pages ────────────────────────────────────────────────────────────────────

@router.get("/pages", response_model=list[CmsPageOut], summary="List all pages")
async def list_pages(
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
    page_status: str | None = Query(None, alias="status"),
):
    pages = await svc.list_pages(status=page_status)
    return pages


@router.post("/pages", response_model=CmsPageOut, status_code=status.HTTP_201_CREATED, summary="Create page")
async def create_page(
    body: CmsPageCreate,
    user: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    data = body.model_dump(exclude_unset=True)
    page = await svc.create_page(data, created_by=user.get("id"))
    return page


@router.get("/pages/{page_id}", response_model=CmsPageOut, summary="Get page with sections and scripts")
async def get_page(
    page_id: str,
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    page = await svc.get_page(page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


@router.patch("/pages/{page_id}", response_model=CmsPageOut, summary="Update page")
async def update_page(
    page_id: str,
    body: CmsPageUpdate,
    user: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    data = body.model_dump(exclude_unset=True)
    page = await svc.update_page(page_id, data, updated_by=user.get("id"))
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


@router.delete("/pages/{page_id}", summary="Delete page")
async def delete_page(
    page_id: str,
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    deleted = await svc.delete_page(page_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return {"deleted": True}


@router.post("/pages/{page_id}/publish", response_model=CmsPageOut, summary="Publish page")
async def publish_page(
    page_id: str,
    user: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    page = await svc.publish_page(page_id, updated_by=user.get("id"))
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


@router.post("/pages/{page_id}/unpublish", response_model=CmsPageOut, summary="Unpublish page")
async def unpublish_page(
    page_id: str,
    user: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    page = await svc.unpublish_page(page_id, updated_by=user.get("id"))
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


@router.post("/pages/{page_id}/duplicate", response_model=CmsPageOut, status_code=status.HTTP_201_CREATED, summary="Duplicate page")
async def duplicate_page(
    page_id: str,
    user: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    page = await svc.duplicate_page(page_id, created_by=user.get("id"))
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


# ─── Sections ─────────────────────────────────────────────────────────────────

@router.post("/pages/{page_id}/sections", response_model=CmsSectionOut, status_code=status.HTTP_201_CREATED, summary="Add section to page")
async def create_section(
    page_id: str,
    body: CmsSectionCreate,
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    data = body.model_dump(exclude_unset=True)
    section = await svc.create_section(page_id, data)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return section


@router.put("/pages/{page_id}/sections/reorder", response_model=list[CmsSectionOut], summary="Reorder sections")
async def reorder_sections(
    page_id: str,
    body: ReorderRequest,
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    items = [item.model_dump() for item in body.items]
    return await svc.reorder_sections(page_id, items)


@router.patch("/sections/{section_id}", response_model=CmsSectionOut, summary="Update section")
async def update_section(
    section_id: str,
    body: CmsSectionUpdate,
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    data = body.model_dump(exclude_unset=True)
    section = await svc.update_section(section_id, data)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return section


@router.delete("/sections/{section_id}", summary="Delete section")
async def delete_section(
    section_id: str,
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    deleted = await svc.delete_section(section_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return {"deleted": True}


# ─── Scripts ──────────────────────────────────────────────────────────────────

@router.get("/scripts", response_model=list[CmsScriptOut], summary="List scripts (global or per page)")
async def list_scripts(
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
    page_id: str | None = Query(None),
):
    return await svc.list_scripts(page_id=page_id)


@router.post("/scripts", response_model=CmsScriptOut, status_code=status.HTTP_201_CREATED, summary="Create script")
async def create_script(
    body: CmsScriptCreate,
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    data = body.model_dump(exclude_unset=True)
    return await svc.create_script(data)


@router.patch("/scripts/{script_id}", response_model=CmsScriptOut, summary="Update script")
async def update_script(
    script_id: str,
    body: CmsScriptUpdate,
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    data = body.model_dump(exclude_unset=True)
    script = await svc.update_script(script_id, data)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found")
    return script


@router.delete("/scripts/{script_id}", summary="Delete script")
async def delete_script(
    script_id: str,
    _: SuperuserDep,
    svc: CmsService = Depends(_svc),
):
    deleted = await svc.delete_script(script_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found")
    return {"deleted": True}
