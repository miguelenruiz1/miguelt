"""Repository for StockMovement (immutable log)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import MovementType, StockMovement
from app.db.models.entity import Product


class MovementRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> StockMovement:
        movement = StockMovement(id=str(uuid.uuid4()), **data)
        self.db.add(movement)
        await self.db.flush()
        await self.db.refresh(movement)
        return movement

    async def list(
        self,
        tenant_id: str,
        product_id: str | None = None,
        movement_type: MovementType | None = None,
        status: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StockMovement], int]:
        q = select(StockMovement).where(StockMovement.tenant_id == tenant_id)
        if product_id:
            q = q.where(StockMovement.product_id == product_id)
        if movement_type:
            q = q.where(StockMovement.movement_type == movement_type)
        if status:
            q = q.where(StockMovement.status == status)
        if from_dt:
            q = q.where(StockMovement.created_at >= from_dt)
        if to_dt:
            q = q.where(StockMovement.created_at <= to_dt)
        if search:
            like = f"%{search}%"
            q = q.join(Product, StockMovement.product_id == Product.id).where(
                or_(
                    StockMovement.reference.ilike(like),
                    StockMovement.notes.ilike(like),
                    StockMovement.batch_number.ilike(like),
                    StockMovement.performed_by.ilike(like),
                    Product.name.ilike(like),
                    Product.sku.ilike(like),
                )
            )
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = (
            q.options(
                joinedload(StockMovement.product),
                joinedload(StockMovement.from_warehouse),
                joinedload(StockMovement.to_warehouse),
            )
            .order_by(StockMovement.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(q)
        return list(result.scalars().unique().all()), total
