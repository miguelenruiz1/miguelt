"""Internal S2S endpoints — called by other services (trace-service, etc.)

Auth: X-Service-Token header (shared secret, NOT user JWT).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.session import get_db_session

router = APIRouter(prefix="/api/v1/internal", tags=["internal-s2s"])


async def _verify_service_token(
    x_service_token: str = Header(..., alias="X-Service-Token"),
) -> str:
    settings = get_settings()
    import secrets as _secrets
    if not _secrets.compare_digest(x_service_token or "", settings.S2S_SERVICE_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
        )
    return x_service_token


# ─── Schemas ────────────────────────────────────────────────────────────────

class BatchInfoResponse(BaseModel):
    id: str
    batch_number: str
    entity_id: str
    quantity: float
    manufacture_date: str | None = None
    expiry_date: str | None = None

    class Config:
        from_attributes = True


# ─── GET /internal/batches/{batch_id} ───────────────────────────────────────

@router.get(
    "/batches/{batch_id}",
    response_model=BatchInfoResponse,
    dependencies=[Depends(_verify_service_token)],
)
async def get_batch_info(
    batch_id: str,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db_session),
) -> BatchInfoResponse:
    """
    Called by trace-service to get batch details for trazability.
    Returns batch_number, expiry_date, manufacture_date, entity_id, quantity.

    Tenant-scoped: requires X-Tenant-Id header so a compromised S2S token
    can't enumerate batches across tenants.
    """
    from app.db.models.tracking import EntityBatch

    result = await db.execute(
        select(EntityBatch).where(
            EntityBatch.id == batch_id,
            EntityBatch.tenant_id == x_tenant_id,
        )
    )
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{batch_id}' not found",
        )

    return BatchInfoResponse(
        id=batch.id,
        batch_number=batch.batch_number,
        entity_id=batch.entity_id,
        quantity=float(batch.quantity),
        manufacture_date=batch.manufacture_date.isoformat() if batch.manufacture_date else None,
        expiry_date=batch.expiration_date.isoformat() if batch.expiration_date else None,
    )
