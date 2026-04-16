"""Repository for unmatched payment ledger (FASE2)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UnmatchedPayment


class UnmatchedPaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        gateway_slug: str,
        gateway_tx_id: str,
        reference: str | None,
        amount: float | None,
        currency: str | None,
        raw_payload: dict | None,
        notes: str | None = None,
    ) -> UnmatchedPayment | None:
        """Insert a record idempotently (UNIQUE on (gateway_slug, gateway_tx_id)).

        Uses savepoint to avoid polluting the outer transaction if the row
        already exists (regla #2).
        """
        try:
            async with self.db.begin_nested():
                row = UnmatchedPayment(
                    id=str(uuid.uuid4()),
                    gateway_slug=gateway_slug,
                    gateway_tx_id=gateway_tx_id,
                    reference=reference,
                    amount=amount,
                    currency=currency,
                    raw_payload=raw_payload,
                    notes=notes,
                )
                self.db.add(row)
                await self.db.flush()
                return row
        except Exception:
            return None

    async def list_unresolved(self, limit: int = 100) -> list[UnmatchedPayment]:
        result = await self.db.execute(
            select(UnmatchedPayment)
            .where(UnmatchedPayment.resolved_at.is_(None))
            .order_by(UnmatchedPayment.received_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_resolved(self, unmatched_id: str, invoice_id: str) -> None:
        row = await self.db.get(UnmatchedPayment, unmatched_id)
        if row is None:
            return
        row.resolved_at = datetime.now(timezone.utc)
        row.resolved_invoice_id = invoice_id
        await self.db.flush()
