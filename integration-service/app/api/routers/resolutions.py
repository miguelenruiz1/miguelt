"""Invoice resolution CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db_session
from app.domain.schemas.integration import InvoiceResolutionCreate, InvoiceResolutionOut
from app.services.resolution_service import ResolutionService

router = APIRouter(prefix="/api/v1/resolutions", tags=["resolutions"])

Manager = Depends(require_permission("integrations.manage"))


@router.get("/{provider}", response_model=InvoiceResolutionOut)
async def get_resolution(
    provider: str,
    user: dict = Manager,
    db: AsyncSession = Depends(get_db_session),
):
    """Get the active resolution for this tenant and provider."""
    svc = ResolutionService(db)
    resolution = await svc.get_active_resolution(user["tenant_id"], provider)
    if not resolution:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay resolución configurada para este proveedor",
        )
    return resolution


@router.post("/{provider}", response_model=InvoiceResolutionOut, status_code=201)
async def create_resolution(
    provider: str,
    body: InvoiceResolutionCreate,
    user: dict = Manager,
    db: AsyncSession = Depends(get_db_session),
):
    """Create or replace the active resolution for this tenant and provider."""
    svc = ResolutionService(db)
    data = body.model_dump()
    data["provider"] = provider
    return await svc.create_resolution(user["tenant_id"], data)


@router.delete("/{provider}", status_code=204)
async def deactivate_resolution(
    provider: str,
    user: dict = Manager,
    db: AsyncSession = Depends(get_db_session),
):
    """Deactivate the current resolution (keeps history, sets is_active=False)."""
    svc = ResolutionService(db)
    await svc.deactivate_resolution(user["tenant_id"], provider)
