"""Business logic for batch quality tests."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models.tracking import BatchQualityTest, EntityBatch


def _derive_passed(
    value: Decimal,
    threshold_min: Decimal | None,
    threshold_max: Decimal | None,
) -> bool | None:
    """Return True/False when at least one threshold is set, else None."""
    if threshold_min is None and threshold_max is None:
        return None
    if threshold_min is not None and value < threshold_min:
        return False
    if threshold_max is not None and value > threshold_max:
        return False
    return True


class QualityTestService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _ensure_batch(self, tenant_id: str, batch_id: str) -> EntityBatch:
        batch = (
            await self.db.execute(
                select(EntityBatch).where(
                    EntityBatch.tenant_id == tenant_id,
                    EntityBatch.id == batch_id,
                )
            )
        ).scalar_one_or_none()
        if batch is None:
            raise NotFoundError(f"Lote '{batch_id}' no encontrado")
        return batch

    async def create(self, tenant_id: str, data: dict) -> BatchQualityTest:
        batch_id = data["batch_id"]
        await self._ensure_batch(tenant_id, batch_id)

        passed = _derive_passed(
            Decimal(str(data["value"])),
            Decimal(str(data["threshold_min"])) if data.get("threshold_min") is not None else None,
            Decimal(str(data["threshold_max"])) if data.get("threshold_max") is not None else None,
        )
        row = BatchQualityTest(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            batch_id=batch_id,
            test_type=data["test_type"],
            value=data["value"],
            unit=data["unit"],
            threshold_min=data.get("threshold_min"),
            threshold_max=data.get("threshold_max"),
            passed=passed,
            lab=data.get("lab"),
            test_date=data["test_date"],
            doc_hash=data.get("doc_hash"),
            notes=data.get("notes"),
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def list_for_batch(self, tenant_id: str, batch_id: str) -> list[BatchQualityTest]:
        await self._ensure_batch(tenant_id, batch_id)
        rows = (
            await self.db.execute(
                select(BatchQualityTest)
                .where(
                    BatchQualityTest.tenant_id == tenant_id,
                    BatchQualityTest.batch_id == batch_id,
                )
                .order_by(BatchQualityTest.test_date.desc(), BatchQualityTest.created_at.desc())
            )
        ).scalars().all()
        return list(rows)
