"""Cycle count business logic: create, count, approve with IRA computation."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.errors import NotFoundError, ValidationError
from app.db.models import (
    CycleCount, CycleCountItem, CycleCountStatus,
    Product, StockLevel,
)
from app.repositories.cycle_count_repo import CycleCountRepository
from app.repositories.stock_repo import StockRepository
from app.services.stock_service import StockService


class CycleCountService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CycleCountRepository(db)
        self.stock_repo = StockRepository(db)
        self.stock_service = StockService(db)

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _get_count(self, cc_id: str, tenant_id: str) -> CycleCount:
        cc = await self.repo.get_by_id(cc_id, tenant_id)
        if not cc:
            raise NotFoundError(f"Cycle count {cc_id!r} not found")
        return cc

    def _assert_status(self, cc: CycleCount, *allowed: CycleCountStatus):
        if cc.status not in allowed:
            raise ValidationError(
                f"Cannot perform this action: count is '{cc.status.value}', "
                f"expected {[s.value for s in allowed]}"
            )

    # ── Create ───────────────────────────────────────────────────────────

    async def create_count(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_ids: list[str] | None = None,
        methodology: str | None = None,
        assigned_counters: int = 1,
        minutes_per_count: int = 2,
        scheduled_date: datetime | None = None,
        notes: str | None = None,
        created_by: str | None = None,
    ) -> CycleCount:
        count_number = await self.repo.next_count_number(tenant_id)

        cc = await self.repo.create({
            "tenant_id": tenant_id,
            "count_number": count_number,
            "warehouse_id": warehouse_id,
            "status": CycleCountStatus.draft,
            "methodology": methodology,
            "assigned_counters": assigned_counters,
            "minutes_per_count": minutes_per_count,
            "scheduled_date": scheduled_date,
            "notes": notes,
            "created_by": created_by,
        })

        # Determine which products to include
        if product_ids:
            # Only specified products
            levels = []
            for pid in product_ids:
                level = await self.stock_repo.get_level(pid, warehouse_id)
                levels.append((pid, level))
        else:
            # All products with stock in this warehouse
            all_levels = await self.stock_repo.list_levels(tenant_id, warehouse_id=warehouse_id)
            levels = [(sl.product_id, sl) for sl in all_levels]

        # Create snapshot items
        items_data = []
        for product_id, level in levels:
            system_qty = level.qty_on_hand if level else Decimal("0")
            items_data.append({
                "tenant_id": tenant_id,
                "cycle_count_id": cc.id,
                "product_id": product_id,
                "location_id": level.location_id if level else None,
                "batch_id": level.batch_id if level else None,
                "system_qty": system_qty,
            })

        if items_data:
            await self.repo.create_items_bulk(items_data)

        # Re-fetch with relationships
        return await self._get_count(cc.id, tenant_id)

    # ── State transitions ────────────────────────────────────────────────

    async def start_count(self, cc_id: str, tenant_id: str) -> CycleCount:
        cc = await self._get_count(cc_id, tenant_id)
        self._assert_status(cc, CycleCountStatus.draft)
        now = datetime.now(timezone.utc)
        await self.repo.update_status(cc, CycleCountStatus.in_progress, started_at=now)
        return await self._get_count(cc.id, tenant_id)

    async def complete_count(self, cc_id: str, tenant_id: str) -> CycleCount:
        cc = await self._get_count(cc_id, tenant_id)
        self._assert_status(cc, CycleCountStatus.in_progress)

        # Validate all items have been counted
        uncounted = [i for i in cc.items if i.counted_qty is None]
        if uncounted:
            raise ValidationError(
                f"{len(uncounted)} item(s) have not been counted yet"
            )

        now = datetime.now(timezone.utc)
        await self.repo.update_status(cc, CycleCountStatus.completed, completed_at=now)
        return await self._get_count(cc.id, tenant_id)

    async def approve_count(
        self, cc_id: str, tenant_id: str, approved_by: str | None = None,
    ) -> CycleCount:
        cc = await self._get_count(cc_id, tenant_id)
        self._assert_status(cc, CycleCountStatus.completed)

        now = datetime.now(timezone.utc)

        # Apply adjustments for each item with discrepancy != 0
        # IMPORTANT: Use delta-based correction. Between count and approval,
        # legitimate movements (purchases, sales) may have changed stock.
        # We apply the discrepancy (error correction) to CURRENT stock,
        # not set to the absolute counted_qty. This prevents erasing
        # legitimate movements that occurred after the count.
        for item in cc.items:
            if item.discrepancy and item.discrepancy != Decimal("0"):
                level = await self.stock_repo.get_level(item.product_id, cc.warehouse_id)
                current_qty = level.qty_on_hand if level else Decimal("0")
                # discrepancy = counted_qty - system_qty (at count time)
                # Apply that delta to the current stock
                adjusted_qty = max(Decimal("0"), current_qty + item.discrepancy)
                movement = await self.stock_service.adjust(
                    tenant_id=tenant_id,
                    product_id=item.product_id,
                    warehouse_id=cc.warehouse_id,
                    new_qty=adjusted_qty,
                    reason=f"Conteo ciclico {cc.count_number}: discrepancia {item.discrepancy:+}",
                    performed_by=approved_by,
                )
                await self.repo.update_item(item, movement_id=movement.id)

            # Update last_count_at on StockLevel
            level = await self.stock_repo.get_level(item.product_id, cc.warehouse_id)
            if level:
                level.last_count_at = now
                await self.db.flush()

        # Compute and save IRA snapshot
        ira = self._compute_ira(cc)
        await self.repo.create_ira_snapshot({
            "tenant_id": tenant_id,
            "cycle_count_id": cc.id,
            "warehouse_id": cc.warehouse_id,
            "total_items": ira["total_items"],
            "accurate_items": ira["accurate_items"],
            "ira_percentage": Decimal(str(round(ira["ira_percentage"], 2))),
            "total_system_value": Decimal(str(round(ira["total_system_value"], 2))),
            "total_counted_value": Decimal(str(round(ira["total_counted_value"], 2))),
            "value_accuracy": Decimal(str(round(ira["value_accuracy"], 2))),
            "snapshot_date": now,
        })

        await self.repo.update_status(
            cc, CycleCountStatus.approved, approved_at=now, approved_by=approved_by
        )
        return await self._get_count(cc.id, tenant_id)

    async def cancel_count(self, cc_id: str, tenant_id: str) -> CycleCount:
        cc = await self._get_count(cc_id, tenant_id)
        self._assert_status(
            cc, CycleCountStatus.draft, CycleCountStatus.in_progress, CycleCountStatus.completed
        )
        await self.repo.update_status(cc, CycleCountStatus.canceled)
        return await self._get_count(cc.id, tenant_id)

    # ── Record count ─────────────────────────────────────────────────────

    async def record_item_count(
        self,
        cc_id: str,
        item_id: str,
        tenant_id: str,
        counted_qty: Decimal,
        counted_by: str | None = None,
        notes: str | None = None,
    ) -> CycleCountItem:
        cc = await self._get_count(cc_id, tenant_id)
        self._assert_status(cc, CycleCountStatus.in_progress)

        item = await self.repo.get_item(item_id, cc_id)
        if not item:
            raise NotFoundError(f"Cycle count item {item_id!r} not found")

        discrepancy = counted_qty - item.system_qty
        now = datetime.now(timezone.utc)

        await self.repo.update_item(
            item,
            counted_qty=counted_qty,
            discrepancy=discrepancy,
            counted_by=counted_by,
            counted_at=now,
            notes=notes,
        )
        return item

    # ── Recount (second count attempt per video methodology) ────────────

    async def recount_item(
        self,
        cc_id: str,
        item_id: str,
        tenant_id: str,
        recount_qty: Decimal,
        root_cause: str | None = None,
        counted_by: str | None = None,
        notes: str | None = None,
    ) -> CycleCountItem:
        """Second count for items with discrepancy. Updates final discrepancy
        based on recount. Per video: system gives 2 count opportunities."""
        cc = await self._get_count(cc_id, tenant_id)
        self._assert_status(cc, CycleCountStatus.in_progress)

        item = await self.repo.get_item(item_id, cc_id)
        if not item:
            raise NotFoundError(f"Cycle count item {item_id!r} not found")

        if item.counted_qty is None:
            raise ValidationError("Item must be counted first before recount")

        recount_discrepancy = recount_qty - item.system_qty
        # The recount becomes the authoritative count
        final_discrepancy = recount_discrepancy

        await self.repo.update_item(
            item,
            recount_qty=recount_qty,
            recount_discrepancy=recount_discrepancy,
            root_cause=root_cause,
            # Update the main discrepancy to reflect the recount
            counted_qty=recount_qty,
            discrepancy=final_discrepancy,
            counted_by=counted_by,
            counted_at=datetime.now(timezone.utc),
            notes=notes or item.notes,
        )
        return item

    # ── Feasibility calculator (per video: time/personnel analysis) ───

    def compute_feasibility(self, cc: CycleCount) -> dict:
        """Calculate if the count is feasible given personnel and time.
        Based on the Brain Logistic video formula:
          total_minutes = items × minutes_per_count
          total_hours = total_minutes / 60
          hours_per_counter = total_hours / assigned_counters
          feasible if hours_per_counter <= available_hours (7h)
        """
        total_items = len(cc.items)
        minutes_per_count = cc.minutes_per_count or 2
        assigned_counters = cc.assigned_counters or 1
        available_hours = 7.0

        total_minutes = total_items * minutes_per_count
        total_hours = total_minutes / 60
        hours_per_counter = total_hours / assigned_counters if assigned_counters > 0 else total_hours
        is_feasible = hours_per_counter <= available_hours

        return {
            "total_items": total_items,
            "minutes_per_count": minutes_per_count,
            "assigned_counters": assigned_counters,
            "total_minutes": round(total_minutes, 1),
            "total_hours": round(total_hours, 1),
            "hours_per_counter": round(hours_per_counter, 1),
            "available_hours": available_hours,
            "is_feasible": is_feasible,
        }

    # ── IRA computation ──────────────────────────────────────────────────

    def _compute_ira(self, cc: CycleCount) -> dict:
        """Compute IRA metrics from a cycle count's items (in-memory)."""
        total_items = len(cc.items)
        accurate_items = 0
        total_system_value = Decimal("0")
        total_counted_value = Decimal("0")
        counted_items = 0

        for item in cc.items:
            if item.counted_qty is None:
                continue
            counted_items += 1

            cost = Decimal("0")
            if item.product and hasattr(item.product, "cost_price") and item.product.cost_price:
                cost = item.product.cost_price

            total_system_value += item.system_qty * cost
            total_counted_value += item.counted_qty * cost

            if item.discrepancy == Decimal("0"):
                accurate_items += 1

        ira_percentage = (accurate_items / total_items * 100) if total_items > 0 else 0.0
        value_accuracy = 0.0
        if total_system_value > 0:
            abs_diff = abs(total_system_value - total_counted_value)
            value_accuracy = float((1 - abs_diff / total_system_value) * 100)

        return {
            "total_items": total_items,
            "accurate_items": accurate_items,
            "ira_percentage": float(ira_percentage),
            "total_system_value": float(total_system_value),
            "total_counted_value": float(total_counted_value),
            "value_accuracy": value_accuracy,
            "counted_items": counted_items,
        }

    async def compute_ira(self, cc_id: str, tenant_id: str) -> dict:
        cc = await self._get_count(cc_id, tenant_id)
        return self._compute_ira(cc)

    # ── Analytics ────────────────────────────────────────────────────────

    async def get_ira_trend(self, tenant_id: str, warehouse_id: str | None = None) -> list[dict]:
        snapshots = await self.repo.list_ira_snapshots(tenant_id, warehouse_id=warehouse_id)
        return [
            {
                "date": s.snapshot_date.isoformat(),
                "ira_percentage": float(s.ira_percentage),
                "value_accuracy": float(s.value_accuracy),
                "total_items": s.total_items,
                "accurate_items": s.accurate_items,
            }
            for s in reversed(snapshots)  # chronological order
        ]

    async def get_product_discrepancy_history(
        self, tenant_id: str, product_id: str,
    ) -> list[dict]:
        return await self.repo.product_discrepancy_history(tenant_id, product_id)
