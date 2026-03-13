"""Repository for CycleCount, CycleCountItem, and IRASnapshot operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import CycleCount, CycleCountItem, CycleCountStatus, IRASnapshot


class CycleCountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Count number generation ──────────────────────────────────────────

    async def next_count_number(self, tenant_id: str) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"CC-{year}-"
        result = await self.db.execute(
            select(func.count())
            .where(
                CycleCount.tenant_id == tenant_id,
                CycleCount.count_number.like(f"{prefix}%"),
            )
        )
        seq = result.scalar_one() + 1
        return f"{prefix}{seq:04d}"

    # ── Cycle counts CRUD ────────────────────────────────────────────────

    async def create(self, data: dict) -> CycleCount:
        cc = CycleCount(id=str(uuid.uuid4()), **data)
        self.db.add(cc)
        await self.db.flush()
        await self.db.refresh(cc)
        return cc

    async def get_by_id(self, cc_id: str, tenant_id: str) -> CycleCount | None:
        result = await self.db.execute(
            select(CycleCount)
            .options(
                joinedload(CycleCount.warehouse),
                joinedload(CycleCount.items).joinedload(CycleCountItem.product),
                joinedload(CycleCount.ira_snapshot),
            )
            .where(CycleCount.id == cc_id, CycleCount.tenant_id == tenant_id)
        )
        return result.unique().scalar_one_or_none()

    async def list_counts(
        self,
        tenant_id: str,
        status: str | None = None,
        warehouse_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[CycleCount], int]:
        q = (
            select(CycleCount)
            .options(joinedload(CycleCount.warehouse))
            .where(CycleCount.tenant_id == tenant_id)
        )
        count_q = select(func.count()).select_from(CycleCount).where(CycleCount.tenant_id == tenant_id)

        if status:
            q = q.where(CycleCount.status == status)
            count_q = count_q.where(CycleCount.status == status)
        if warehouse_id:
            q = q.where(CycleCount.warehouse_id == warehouse_id)
            count_q = count_q.where(CycleCount.warehouse_id == warehouse_id)

        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        q = q.order_by(CycleCount.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        items = list(result.unique().scalars().all())
        return items, total

    async def update_status(
        self, cc: CycleCount, status: CycleCountStatus, **kwargs
    ) -> CycleCount:
        cc.status = status
        for k, v in kwargs.items():
            setattr(cc, k, v)
        await self.db.flush()
        await self.db.refresh(cc)
        return cc

    # ── Items ────────────────────────────────────────────────────────────

    async def create_items_bulk(self, items: list[dict]) -> list[CycleCountItem]:
        objs = []
        for data in items:
            item = CycleCountItem(id=str(uuid.uuid4()), **data)
            self.db.add(item)
            objs.append(item)
        await self.db.flush()
        for obj in objs:
            await self.db.refresh(obj)
        return objs

    async def get_item(self, item_id: str, cycle_count_id: str) -> CycleCountItem | None:
        result = await self.db.execute(
            select(CycleCountItem)
            .options(joinedload(CycleCountItem.product))
            .where(
                CycleCountItem.id == item_id,
                CycleCountItem.cycle_count_id == cycle_count_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def update_item(self, item: CycleCountItem, **kwargs) -> CycleCountItem:
        for k, v in kwargs.items():
            setattr(item, k, v)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    # ── IRA snapshots ────────────────────────────────────────────────────

    async def create_ira_snapshot(self, data: dict) -> IRASnapshot:
        snap = IRASnapshot(id=str(uuid.uuid4()), **data)
        self.db.add(snap)
        await self.db.flush()
        await self.db.refresh(snap)
        return snap

    async def list_ira_snapshots(
        self,
        tenant_id: str,
        warehouse_id: str | None = None,
        limit: int = 50,
    ) -> list[IRASnapshot]:
        q = (
            select(IRASnapshot)
            .where(IRASnapshot.tenant_id == tenant_id)
        )
        if warehouse_id:
            q = q.where(IRASnapshot.warehouse_id == warehouse_id)
        q = q.order_by(IRASnapshot.snapshot_date.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # ── Product discrepancy history ──────────────────────────────────────

    async def product_discrepancy_history(
        self, tenant_id: str, product_id: str, limit: int = 20,
    ) -> list[dict]:
        q = (
            select(
                CycleCountItem.cycle_count_id,
                CycleCount.count_number,
                CycleCount.warehouse_id,
                CycleCountItem.system_qty,
                CycleCountItem.counted_qty,
                CycleCountItem.discrepancy,
                CycleCountItem.counted_at,
            )
            .join(CycleCount, CycleCountItem.cycle_count_id == CycleCount.id)
            .where(
                CycleCountItem.tenant_id == tenant_id,
                CycleCountItem.product_id == product_id,
                CycleCountItem.counted_qty.isnot(None),
            )
            .order_by(CycleCountItem.counted_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(q)
        rows = result.fetchall()
        return [
            {
                "cycle_count_id": r.cycle_count_id,
                "count_number": r.count_number,
                "warehouse_id": r.warehouse_id,
                "system_qty": float(r.system_qty),
                "counted_qty": float(r.counted_qty) if r.counted_qty is not None else None,
                "discrepancy": float(r.discrepancy) if r.discrepancy is not None else None,
                "counted_at": r.counted_at.isoformat() if r.counted_at else None,
            }
            for r in rows
        ]

    # ── Analytics helpers ────────────────────────────────────────────────

    async def count_pending(self, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).where(
                CycleCount.tenant_id == tenant_id,
                CycleCount.status.in_([
                    CycleCountStatus.draft,
                    CycleCountStatus.in_progress,
                    CycleCountStatus.completed,
                ]),
            )
        )
        return result.scalar_one()

    async def latest_ira(self, tenant_id: str) -> float | None:
        result = await self.db.execute(
            select(IRASnapshot.ira_percentage)
            .where(IRASnapshot.tenant_id == tenant_id)
            .order_by(IRASnapshot.snapshot_date.desc())
            .limit(1)
        )
        val = result.scalar_one_or_none()
        return float(val) if val is not None else None
