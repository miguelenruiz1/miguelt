"""Stock movements log endpoint."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse

from app.api.deps import ModuleUser, require_permission
from app.db.models import MovementType
from app.db.session import get_db_session
from app.domain.schemas import PaginatedMovements, StockMovementOut
from app.repositories.movement_repo import MovementRepository
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/movements", tags=["movements"])


@router.get("", response_model=PaginatedMovements)
async def list_movements(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    product_id: str | None = None,
    movement_type: MovementType | None = None,
    status: str | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> ORJSONResponse:
    repo = MovementRepository(db)
    items, total = await repo.list(
        tenant_id=current_user["tenant_id"],
        product_id=product_id,
        movement_type=movement_type,
        status=status,
        from_dt=from_dt,
        to_dt=to_dt,
        search=search,
        offset=offset,
        limit=limit,
    )
    return ORJSONResponse({
        "items": [StockMovementOut.model_validate(m).model_dump(mode="json") for m in items],
        "total": total,
        "offset": offset,
        "limit": limit,
    })
