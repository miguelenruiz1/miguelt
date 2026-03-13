"""Repository for Invoice operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invoice, InvoiceStatus


class InvoiceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> Invoice:
        invoice = Invoice(id=str(uuid.uuid4()), **data)
        self.db.add(invoice)
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def get_by_id(self, invoice_id: str) -> Invoice | None:
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def list_by_subscription(self, subscription_id: str) -> list[Invoice]:
        result = await self.db.execute(
            select(Invoice)
            .where(Invoice.subscription_id == subscription_id)
            .order_by(Invoice.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, invoice: Invoice, data: dict) -> Invoice:
        for k, v in data.items():
            setattr(invoice, k, v)
        invoice.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def next_invoice_number(self) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"INV-{year}-"
        result = await self.db.execute(
            select(func.max(Invoice.invoice_number))
            .where(Invoice.invoice_number.like(f"{prefix}%"))
        )
        last = result.scalar_one_or_none()
        if last:
            try:
                seq = int(last.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"
