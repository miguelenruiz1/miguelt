"""WM inventory service: stock states, bin blocking, ERI (record accuracy)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import (
    CycleCount, CycleCountItem, IRASnapshot, StockLevel, WarehouseLocation,
)
from app.domain.schemas.wm_inventory import (
    ERIOut, StockStatusBucket, StockStatusOut,
)


class WMInventoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def block_bin(self, tenant_id: str, location_id: str, inbound: bool, outbound: bool, reason: str | None):
        loc = await self._get_location(tenant_id, location_id)
        loc.blocked_inbound = inbound
        loc.blocked_outbound = outbound
        loc.block_reason = reason
        await self.db.flush()
        return loc

    async def unblock_bin(self, tenant_id: str, location_id: str):
        loc = await self._get_location(tenant_id, location_id)
        loc.blocked_inbound = False
        loc.blocked_outbound = False
        loc.block_reason = None
        await self.db.flush()
        return loc

    async def _get_location(self, tenant_id: str, location_id: str) -> WarehouseLocation:
        loc = (await self.db.execute(
            select(WarehouseLocation).where(
                WarehouseLocation.tenant_id == tenant_id, WarehouseLocation.id == location_id,
            )
        )).scalar_one_or_none()
        if not loc:
            raise NotFoundError(f"Location {location_id!r} not found")
        return loc

    async def set_stock_state(self, tenant_id: str, stock_level_id: str, stock_type: str) -> StockLevel:
        sl = (await self.db.execute(
            select(StockLevel).where(
                StockLevel.tenant_id == tenant_id, StockLevel.id == stock_level_id,
            )
        )).scalar_one_or_none()
        if not sl:
            raise NotFoundError(f"Stock level {stock_level_id!r} not found")
        sl.stock_type = stock_type
        await self.db.flush()
        return sl

    async def stock_status(self, tenant_id: str, warehouse_id: str) -> StockStatusOut:
        rows = (await self.db.execute(
            select(
                StockLevel.stock_type,
                func.count().label("quants"),
                func.coalesce(func.sum(StockLevel.qty_on_hand), 0).label("total_qty"),
            ).where(
                StockLevel.tenant_id == tenant_id,
                StockLevel.warehouse_id == warehouse_id,
            ).group_by(StockLevel.stock_type)
        )).all()
        return StockStatusOut(
            warehouse_id=warehouse_id,
            buckets=[
                StockStatusBucket(stock_type=r[0] or "available", quants=int(r[1]), total_qty=Decimal(r[2]))
                for r in rows
            ],
        )

    async def compute_eri(self, tenant_id: str, warehouse_id: str) -> ERIOut:
        # Items from completed/approved cycle counts in this warehouse.
        rows = list((await self.db.execute(
            select(CycleCountItem.system_qty, CycleCountItem.counted_qty)
            .join(CycleCount, CycleCount.id == CycleCountItem.cycle_count_id)
            .where(
                CycleCount.tenant_id == tenant_id,
                CycleCount.warehouse_id == warehouse_id,
                CycleCount.status.in_(["completed", "approved"]),
                CycleCountItem.counted_qty.is_not(None),
            )
        )).all())
        counted = len(rows)
        accurate = sum(1 for sysq, cq in rows if Decimal(sysq) == Decimal(cq))
        eri = round((accurate / counted * 100), 1) if counted else 0.0

        # Latest value accuracy snapshot, if any.
        snap = (await self.db.execute(
            select(IRASnapshot.value_accuracy).where(
                IRASnapshot.tenant_id == tenant_id,
                IRASnapshot.warehouse_id == warehouse_id,
            ).order_by(IRASnapshot.snapshot_date.desc()).limit(1)
        )).scalar_one_or_none()

        return ERIOut(
            warehouse_id=warehouse_id, items_counted=counted, items_accurate=accurate,
            eri_pct=eri, value_accuracy_pct=float(snap) if snap is not None else None,
        )
