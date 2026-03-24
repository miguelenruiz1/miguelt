"""Router for compliance data by asset — cross-framework view."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.db.session import get_db_session
from app.models.record import ComplianceRecord
from app.schemas.record import RecordResponse

router = APIRouter(
    prefix="/api/v1/compliance/assets",
    tags=["compliance-assets"],
)


def _tenant_id(user: dict) -> uuid.UUID:
    """Extract tenant_id — may be a UUID or a slug string."""
    raw = str(user.get("tenant_id", "00000000-0000-0000-0000-000000000001"))
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/{asset_id}", response_model=list[RecordResponse])
async def get_asset_compliance(
    asset_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Return all compliance records for a given asset. Returns empty list if none exist."""
    tid = _tenant_id(user)
    q = (
        select(ComplianceRecord)
        .where(
            ComplianceRecord.tenant_id == tid,
            ComplianceRecord.asset_id == asset_id,
        )
        .order_by(ComplianceRecord.created_at.desc())
    )
    rows = (await db.execute(q)).scalars().all()
    return rows
