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
        from datetime import datetime, timezone

        from app.db.models.events import (
            EventImpact,
            EventSeverity,
            EventStatus,
            EventType,
            InventoryEvent,
        )

        movement_id = str(uuid.uuid4())
        movement = StockMovement(id=movement_id, **data)
        self.db.add(movement)
        await self.db.flush()

        # --- Auto-create linked inventory event ---
        tenant_id = data.get("tenant_id")
        mt = data.get("movement_type")
        if tenant_id and mt:
            slug = f"sys_{mt.value if hasattr(mt, 'value') else mt}"
            et_result = await self.db.execute(
                select(EventType).where(
                    EventType.tenant_id == tenant_id,
                    EventType.slug == slug,
                )
            )
            event_type = et_result.scalar_one_or_none()

            if event_type:
                sev = (await self.db.execute(
                    select(EventSeverity).where(
                        EventSeverity.tenant_id == tenant_id,
                        EventSeverity.is_active == True,  # noqa: E712
                    ).limit(1)
                )).scalar_one_or_none()
                stat = (await self.db.execute(
                    select(EventStatus).where(
                        EventStatus.tenant_id == tenant_id,
                        EventStatus.is_active == True,  # noqa: E712
                    ).limit(1)
                )).scalar_one_or_none()

                if sev and stat:
                    event = InventoryEvent(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        event_type_id=event_type.id,
                        severity_id=sev.id,
                        status_id=stat.id,
                        warehouse_id=data.get("to_warehouse_id") or data.get("from_warehouse_id"),
                        title=f"{event_type.name} — {data.get('quantity', 0)} uds",
                        description=data.get("notes") or data.get("reference") or "",
                        occurred_at=datetime.now(timezone.utc),
                        reported_by=data.get("performed_by"),
                    )
                    self.db.add(event)
                    await self.db.flush()

                    movement.event_id = event.id

                    impact = EventImpact(
                        id=str(uuid.uuid4()),
                        event_id=event.id,
                        entity_id=data.get("product_id"),
                        quantity_impact=data.get("quantity", 0),
                        movement_id=movement_id,
                        batch_id=data.get("batch_id"),
                        notes=data.get("notes"),
                    )
                    self.db.add(impact)
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
