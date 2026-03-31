"""Repository for production receipts (finished goods receipt)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.production import ProductionReceipt, ProductionReceiptLine


class ReceiptRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def next_receipt_number(self, tenant_id: str) -> str:
        year = datetime.now(tz=timezone.utc).year
        prefix = f"RC-{year}-"
        result = await self._db.execute(
            select(func.count(ProductionReceipt.id))
            .where(
                ProductionReceipt.tenant_id == tenant_id,
                ProductionReceipt.receipt_number.like(f"{prefix}%"),
            )
        )
        count = result.scalar_one() or 0
        return f"{prefix}{count + 1:04d}"

    async def create(
        self,
        tenant_id: str,
        production_run_id: str,
        receipt_number: str,
        receipt_date: datetime,
        output_warehouse_id: str | None,
        notes: str | None,
        performed_by: str | None,
        lines: list[dict],
    ) -> ProductionReceipt:
        receipt = ProductionReceipt(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            production_run_id=production_run_id,
            receipt_number=receipt_number,
            status="posted",
            receipt_date=receipt_date,
            output_warehouse_id=output_warehouse_id,
            notes=notes,
            performed_by=performed_by,
        )
        self._db.add(receipt)
        await self._db.flush()

        for line_data in lines:
            line = ProductionReceiptLine(
                id=str(uuid.uuid4()),
                receipt_id=receipt.id,
                **line_data,
            )
            self._db.add(line)

        await self._db.flush()
        return receipt

    async def get(self, tenant_id: str, receipt_id: str) -> ProductionReceipt | None:
        result = await self._db.execute(
            select(ProductionReceipt)
            .options(selectinload(ProductionReceipt.lines))
            .where(
                ProductionReceipt.id == receipt_id,
                ProductionReceipt.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_run(self, tenant_id: str, run_id: str) -> list[ProductionReceipt]:
        result = await self._db.execute(
            select(ProductionReceipt)
            .options(selectinload(ProductionReceipt.lines))
            .where(
                ProductionReceipt.production_run_id == run_id,
                ProductionReceipt.tenant_id == tenant_id,
            )
            .order_by(ProductionReceipt.created_at.asc())
        )
        return list(result.scalars().all())

    async def total_received(self, run_id: str) -> float:
        """Total received_quantity across all receipts for a run."""
        result = await self._db.execute(
            select(func.coalesce(func.sum(ProductionReceiptLine.received_quantity), 0))
            .join(ProductionReceipt, ProductionReceiptLine.receipt_id == ProductionReceipt.id)
            .where(ProductionReceipt.production_run_id == run_id)
        )
        return float(result.scalar_one())
