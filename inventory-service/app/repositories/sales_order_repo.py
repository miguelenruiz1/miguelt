"""Repository for SalesOrder CRUD."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import SalesOrder, SalesOrderLine, SalesOrderStatus

_SO_OPTIONS = (
    selectinload(SalesOrder.lines).selectinload(SalesOrderLine.product),
    selectinload(SalesOrder.lines).selectinload(SalesOrderLine.variant),
    selectinload(SalesOrder.lines).selectinload(SalesOrderLine.warehouse),
    selectinload(SalesOrder.customer),
    selectinload(SalesOrder.warehouse),
    selectinload(SalesOrder.backorders),
)


class SalesOrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        status: str | None = None,
        customer_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[SalesOrder], int]:
        q = (
            select(SalesOrder)
            .options(*_SO_OPTIONS)
            .where(SalesOrder.tenant_id == tenant_id)
        )
        if status:
            q = q.where(SalesOrder.status == status)
        if customer_id:
            q = q.where(SalesOrder.customer_id == customer_id)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.order_by(SalesOrder.created_at.desc()).offset(offset).limit(limit)
        return list((await self.db.execute(q)).scalars().unique().all()), total

    async def get_by_id(self, order_id: str, tenant_id: str) -> SalesOrder | None:
        return (await self.db.execute(
            select(SalesOrder)
            .options(*_SO_OPTIONS)
            .where(SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id)
        )).scalar_one_or_none()

    async def next_number(self, tenant_id: str) -> str:
        from datetime import datetime
        year = datetime.now(timezone.utc).year
        result = await self.db.execute(
            select(func.count()).where(
                SalesOrder.tenant_id == tenant_id,
                SalesOrder.order_number.like(f"SO-{year}-%"),
            )
        )
        seq = result.scalar_one() + 1
        return f"SO-{year}-{seq:04d}"

    async def next_remission_number(self, tenant_id: str) -> str:
        year = datetime.now(timezone.utc).year
        result = await self.db.execute(
            select(func.count()).where(
                SalesOrder.tenant_id == tenant_id,
                SalesOrder.remission_number.like(f"REM-{year}-%"),
            )
        )
        seq = result.scalar_one() + 1
        return f"REM-{year}-{seq:04d}"

    async def create(self, data: dict, lines: list[dict]) -> SalesOrder:
        from app.services.sales_order_service import recalculate_so_totals

        order = SalesOrder(id=str(uuid.uuid4()), **data)
        self.db.add(order)
        await self.db.flush()
        order_lines = []
        for line_data in lines:
            line = SalesOrderLine(id=str(uuid.uuid4()), tenant_id=order.tenant_id, order_id=order.id, **line_data)
            self.db.add(line)
            order_lines.append(line)
        await self.db.flush()
        # Eagerly load the lines relationship to avoid MissingGreenlet on assignment
        await self.db.refresh(order, ["lines"])
        recalculate_so_totals(order)
        await self.db.flush()
        # Re-fetch with lines eagerly loaded to avoid MissingGreenlet on serialization
        return await self.get_by_id(order.id, order.tenant_id)  # type: ignore[return-value]

    async def update(self, order: SalesOrder, data: dict) -> SalesOrder:
        for k, v in data.items():
            setattr(order, k, v)
        order.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return await self.get_by_id(order.id, order.tenant_id)  # type: ignore[return-value]

    async def set_status(self, order: SalesOrder, new_status: SalesOrderStatus) -> SalesOrder:
        order.status = new_status
        now = datetime.now(timezone.utc)
        order.updated_at = now
        if new_status == SalesOrderStatus.shipped:
            order.shipped_date = now
        elif new_status == SalesOrderStatus.delivered:
            order.delivered_date = now
        await self.db.flush()
        return await self.get_by_id(order.id, order.tenant_id)  # type: ignore[return-value]

    async def update_line_shipped(self, line_id: str, qty_shipped: float) -> SalesOrderLine | None:
        result = await self.db.execute(select(SalesOrderLine).where(SalesOrderLine.id == line_id))
        line = result.scalar_one_or_none()
        if line:
            line.qty_shipped = qty_shipped
            await self.db.flush()
        return line

    async def delete(self, order: SalesOrder) -> None:
        self.db.delete(order)
        await self.db.flush()

    async def count_by_status(self, tenant_id: str) -> dict[str, int]:
        result = await self.db.execute(
            select(SalesOrder.status, func.count())
            .where(SalesOrder.tenant_id == tenant_id)
            .group_by(SalesOrder.status)
        )
        return {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in result.all()}
