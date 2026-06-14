"""WM putaway proposal + removal (FIFO/FEFO/LIFO) planning."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    EntityBatch, Product, ProductWarehouseData, PutawayRule, StockLevel,
    StorageType, WarehouseLocation,
)
from app.domain.schemas.wm_putaway import (
    PutawayProposeOut, RemovalAllocation, RemovalPlanOut,
)


class PutawayService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _occupied_location_ids(self, tenant_id: str) -> set[str]:
        return set((await self.db.execute(
            select(StockLevel.location_id).where(
                StockLevel.tenant_id == tenant_id,
                StockLevel.location_id.is_not(None),
                StockLevel.qty_on_hand > Decimal("0"),
            ).distinct()
        )).scalars().all())

    async def propose(self, tenant_id: str, warehouse_id: str, product_id: str, qty: Decimal) -> PutawayProposeOut:
        product = (await self.db.execute(
            select(Product).where(Product.tenant_id == tenant_id, Product.id == product_id)
        )).scalar_one_or_none()

        # 0. Material master fixed bin wins over everything (SAP fixed bin).
        pwd = (await self.db.execute(
            select(ProductWarehouseData).where(
                ProductWarehouseData.tenant_id == tenant_id,
                ProductWarehouseData.product_id == product_id,
                ProductWarehouseData.warehouse_id == warehouse_id,
            )
        )).scalar_one_or_none()
        if pwd and pwd.fixed_bin_id:
            fixed = (await self.db.execute(
                select(WarehouseLocation).where(WarehouseLocation.id == pwd.fixed_bin_id)
            )).scalar_one_or_none()
            if fixed is not None:
                return PutawayProposeOut(
                    location_id=fixed.id, code=fixed.code, storage_type_id=fixed.storage_type_id,
                    reason="bin fijo del material (gestión de almacenes)",
                )

        # 1. Best-matching putaway rule (product match wins over category/commodity).
        rules = list((await self.db.execute(
            select(PutawayRule).where(
                PutawayRule.tenant_id == tenant_id,
                PutawayRule.warehouse_id == warehouse_id,
                PutawayRule.is_active.is_(True),
            ).order_by(PutawayRule.priority)
        )).scalars().all())

        def rule_matches(r: PutawayRule) -> bool:
            if r.match_product_id:
                return r.match_product_id == product_id
            if r.match_category_id and product is not None:
                return r.match_category_id == getattr(product, "category_id", None)
            if r.match_commodity and product is not None:
                return r.match_commodity == getattr(product, "commodity_type", None)
            return False

        matched = next((r for r in rules if rule_matches(r)), None)

        # 2. Candidate physical bins (optionally constrained by the rule's type/section).
        q = select(WarehouseLocation).where(
            WarehouseLocation.tenant_id == tenant_id,
            WarehouseLocation.warehouse_id == warehouse_id,
            WarehouseLocation.location_kind == "physical",
            WarehouseLocation.is_active.is_(True),
            WarehouseLocation.blocked_inbound.is_(False),
        )
        reason_parts = []
        if matched and matched.dest_storage_type_id:
            q = q.where(WarehouseLocation.storage_type_id == matched.dest_storage_type_id)
            reason_parts.append("regla de putaway (tipo de almacén)")
        if matched and matched.dest_storage_section_id:
            q = q.where(WarehouseLocation.storage_section_id == matched.dest_storage_section_id)
            reason_parts.append("sección")
        bins = list((await self.db.execute(q.order_by(WarehouseLocation.sort_order))).scalars().all())

        occupied = await self._occupied_location_ids(tenant_id)
        unit_weight = getattr(product, "weight_per_unit", None) if product else None

        def fits_capacity(b: WarehouseLocation) -> bool:
            if b.max_weight_kg and unit_weight:
                return Decimal(unit_weight) * Decimal(qty) <= Decimal(b.max_weight_kg)
            return True

        # Prefer empty bins that fit capacity; else any empty bin.
        empty_fit = [b for b in bins if b.id not in occupied and fits_capacity(b)]
        chosen = empty_fit[0] if empty_fit else None
        if chosen is None:
            # Fallback: first empty physical bin anywhere in the warehouse.
            allq = select(WarehouseLocation).where(
                WarehouseLocation.tenant_id == tenant_id,
                WarehouseLocation.warehouse_id == warehouse_id,
                WarehouseLocation.location_kind == "physical",
                WarehouseLocation.is_active.is_(True),
                WarehouseLocation.blocked_inbound.is_(False),
            ).order_by(WarehouseLocation.sort_order)
            allbins = list((await self.db.execute(allq)).scalars().all())
            chosen = next((b for b in allbins if b.id not in occupied), None)
            reason_parts = ["primer bin vacío (sin regla aplicable)"]

        if chosen is None:
            return PutawayProposeOut(reason="No hay ubicaciones vacías disponibles")
        return PutawayProposeOut(
            location_id=chosen.id, code=chosen.code, storage_type_id=chosen.storage_type_id,
            reason="; ".join(reason_parts) or "bin disponible",
        )

    async def removal_plan(
        self, tenant_id: str, warehouse_id: str, product_id: str, qty: Decimal, strategy: str | None,
    ) -> RemovalPlanOut:
        if strategy is None:
            pwd = (await self.db.execute(
                select(ProductWarehouseData).where(
                    ProductWarehouseData.tenant_id == tenant_id,
                    ProductWarehouseData.product_id == product_id,
                    ProductWarehouseData.warehouse_id == warehouse_id,
                )
            )).scalar_one_or_none()
            strategy = pwd.removal_strategy if pwd else None
        strat = strategy or "fefo"
        # Available qty per batch IN THIS WAREHOUSE: only `available` stock_type,
        # net of reservations. Blocked/quality quants and reserved qty are not
        # removable. Batch-less stock has no FEFO/FIFO identity, so it is excluded.
        avail_rows = (await self.db.execute(
            select(
                StockLevel.batch_id,
                func.sum(StockLevel.qty_on_hand - StockLevel.qty_reserved),
            ).where(
                StockLevel.tenant_id == tenant_id,
                StockLevel.product_id == product_id,
                StockLevel.warehouse_id == warehouse_id,
                StockLevel.stock_type == "available",
                StockLevel.batch_id.is_not(None),
            ).group_by(StockLevel.batch_id)
        )).all()
        avail = {bid: q for bid, q in avail_rows if q and q > Decimal("0")}

        batches = list((await self.db.execute(
            select(EntityBatch).where(
                EntityBatch.tenant_id == tenant_id,
                EntityBatch.entity_id == product_id,
                EntityBatch.is_active.is_(True),
                EntityBatch.id.in_(list(avail.keys())),
            )
        )).scalars().all()) if avail else []

        if strat == "fefo":
            batches.sort(key=lambda b: (b.expiration_date is None, b.expiration_date or b.created_at))
        elif strat == "lifo":
            batches.sort(key=lambda b: b.created_at, reverse=True)
        else:  # fifo / fixed_bin → oldest first
            batches.sort(key=lambda b: b.created_at)

        remaining = Decimal(qty)
        allocs: list[RemovalAllocation] = []
        for b in batches:
            if remaining <= 0:
                break
            take = min(Decimal(avail[b.id]), remaining)
            allocs.append(RemovalAllocation(
                batch_id=b.id, batch_number=b.batch_number,
                expiration_date=b.expiration_date.isoformat() if b.expiration_date else None,
                qty=take,
            ))
            remaining -= take

        allocated = Decimal(qty) - remaining
        return RemovalPlanOut(
            strategy=strat, requested_qty=Decimal(qty), allocated_qty=allocated,
            shortfall=remaining if remaining > 0 else Decimal("0"), allocations=allocs,
        )
