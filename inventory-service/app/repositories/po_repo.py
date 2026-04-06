"""Repository for PurchaseOrder and PurchaseOrderLine."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import POStatus, PurchaseOrder, PurchaseOrderLine


class PORepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def next_po_number(self, tenant_id: str) -> str:
        """Race-free PO number via atomic counter (sequence_counters table)."""
        from app.repositories.sequence_repo import SequenceRepository
        year = datetime.now(timezone.utc).year
        scope = f"po-{year}"
        seq = await SequenceRepository(self.db).next_value(tenant_id, scope)
        return f"PO-{year}-{seq:04d}"

    async def list(
        self,
        tenant_id: str,
        status: POStatus | None = None,
        supplier_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[PurchaseOrder], int]:
        base_q = select(PurchaseOrder).where(PurchaseOrder.tenant_id == tenant_id)
        if status:
            base_q = base_q.where(PurchaseOrder.status == status)
        if supplier_id:
            base_q = base_q.where(PurchaseOrder.supplier_id == supplier_id)

        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            base_q
            .options(
                joinedload(PurchaseOrder.supplier),
                joinedload(PurchaseOrder.lines).joinedload(PurchaseOrderLine.product),
                joinedload(PurchaseOrder.lines).joinedload(PurchaseOrderLine.variant),
            )
            .order_by(PurchaseOrder.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(q)
        return list(result.scalars().unique().all()), total

    async def get_by_id(self, po_id: str, tenant_id: str) -> PurchaseOrder | None:
        result = await self.db.execute(
            select(PurchaseOrder)
            .options(
                joinedload(PurchaseOrder.supplier),
                joinedload(PurchaseOrder.lines).joinedload(PurchaseOrderLine.product),
                joinedload(PurchaseOrder.lines).joinedload(PurchaseOrderLine.variant),
            )
            .where(
                PurchaseOrder.id == po_id,
                PurchaseOrder.tenant_id == tenant_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def create(self, data: dict) -> PurchaseOrder:
        lines_data = data.pop("lines", [])
        po = PurchaseOrder(id=str(uuid.uuid4()), **data)
        self.db.add(po)
        await self.db.flush()
        for line in lines_data:
            pol = PurchaseOrderLine(id=str(uuid.uuid4()), tenant_id=po.tenant_id, po_id=po.id, **line)
            self.db.add(pol)
        await self.db.flush()
        await self.db.refresh(po)
        return po

    async def update(self, po: PurchaseOrder, data: dict) -> PurchaseOrder:
        for k, v in data.items():
            setattr(po, k, v)
        po.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(po)
        return po

    async def get_line(self, line_id: str, po_id: str) -> PurchaseOrderLine | None:
        result = await self.db.execute(
            select(PurchaseOrderLine).where(
                PurchaseOrderLine.id == line_id,
                PurchaseOrderLine.po_id == po_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_line(self, line: PurchaseOrderLine, data: dict) -> PurchaseOrderLine:
        for k, v in data.items():
            setattr(line, k, v)
        await self.db.flush()
        return line

    async def delete(self, po: PurchaseOrder) -> None:
        await self.db.delete(po)
        await self.db.flush()
