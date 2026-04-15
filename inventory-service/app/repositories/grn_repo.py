"""Repository for Goods Receipt Notes (GRN)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.goods_receipt import GoodsReceipt, GoodsReceiptLine


class GRNRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def next_grn_number(self, tenant_id: str) -> str:
        year = datetime.now(tz=timezone.utc).year
        prefix = f"GRN-{year}-"
        result = await self._db.execute(
            select(func.count(GoodsReceipt.id)).where(
                GoodsReceipt.tenant_id == tenant_id,
                GoodsReceipt.grn_number.like(f"{prefix}%"),
            )
        )
        count = result.scalar_one() or 0
        return f"{prefix}{count + 1:04d}"

    async def create(
        self,
        *,
        tenant_id: str,
        purchase_order_id: str,
        grn_number: str,
        receipt_date,
        received_by: str | None,
        notes: str | None,
        attachments: list | None,
        has_discrepancy: bool,
        lines: list[dict],
    ) -> GoodsReceipt:
        grn = GoodsReceipt(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            purchase_order_id=purchase_order_id,
            grn_number=grn_number,
            receipt_date=receipt_date,
            received_by=received_by,
            notes=notes,
            attachments=attachments or [],
            has_discrepancy=has_discrepancy,
        )
        self._db.add(grn)
        await self._db.flush()

        for ln in lines:
            self._db.add(
                GoodsReceiptLine(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    grn_id=grn.id,
                    **ln,
                )
            )
        await self._db.flush()
        return grn

    async def get(self, tenant_id: str, grn_id: str) -> GoodsReceipt | None:
        result = await self._db.execute(
            select(GoodsReceipt)
            .options(selectinload(GoodsReceipt.lines))
            .where(
                GoodsReceipt.id == grn_id,
                GoodsReceipt.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_po(self, tenant_id: str, po_id: str) -> list[GoodsReceipt]:
        result = await self._db.execute(
            select(GoodsReceipt)
            .options(selectinload(GoodsReceipt.lines))
            .where(
                GoodsReceipt.tenant_id == tenant_id,
                GoodsReceipt.purchase_order_id == po_id,
            )
            .order_by(GoodsReceipt.created_at.asc())
        )
        return list(result.scalars().all())
