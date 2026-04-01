"""Repository for ProductionRun."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProductionRun


class ProductionRunRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def next_run_number(self, tenant_id: str) -> str:
        from datetime import datetime, timezone
        year = datetime.now(timezone.utc).year
        prefix = f"PR-{year}-"
        result = await self.db.execute(
            select(func.max(ProductionRun.run_number)).where(
                ProductionRun.tenant_id == tenant_id,
                ProductionRun.run_number.like(f"{prefix}%"),
            )
        )
        max_num = result.scalar_one()
        if max_num:
            try:
                seq = int(max_num.replace(prefix, "")) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    async def list(
        self,
        tenant_id: str,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProductionRun], int]:
        q = select(ProductionRun).where(ProductionRun.tenant_id == tenant_id)
        if status:
            q = q.where(ProductionRun.status == status)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(ProductionRun.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, run_id: str) -> ProductionRun | None:
        result = await self.db.execute(
            select(ProductionRun).where(
                ProductionRun.tenant_id == tenant_id, ProductionRun.id == run_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> ProductionRun:
        obj = ProductionRun(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ProductionRun, data: dict) -> ProductionRun:
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def count_this_month(self, tenant_id: str) -> int:
        """Count production runs created since the first day of the current month."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(func.count()).where(
                ProductionRun.tenant_id == tenant_id,
                ProductionRun.created_at >= first_of_month,
            )
        )
        return result.scalar_one()

    async def delete(self, obj: ProductionRun) -> None:
        await self.db.delete(obj)
        await self.db.flush()
