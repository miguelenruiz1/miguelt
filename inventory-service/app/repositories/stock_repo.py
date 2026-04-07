"""Repository for StockLevel operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Product, StockLevel


class StockRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_level_with_relations(
        self, product_id: str, warehouse_id: str, batch_id: str | None = None,
        variant_id: str | None = None,
    ) -> StockLevel | None:
        """Same as get_level but eagerly loads product + warehouse."""
        q = (
            select(StockLevel)
            .options(joinedload(StockLevel.product), joinedload(StockLevel.warehouse), joinedload(StockLevel.location))
            .where(
                StockLevel.product_id == product_id,
                StockLevel.warehouse_id == warehouse_id,
            )
        )
        if batch_id is not None:
            q = q.where(StockLevel.batch_id == batch_id)
        else:
            q = q.where(StockLevel.batch_id.is_(None))
        if variant_id is not None:
            q = q.where(StockLevel.variant_id == variant_id)
        else:
            q = q.where(StockLevel.variant_id.is_(None))
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_level(
        self, product_id: str, warehouse_id: str, batch_id: str | None = None,
        variant_id: str | None = None,
    ) -> StockLevel | None:
        q = select(StockLevel).where(
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
        )
        if batch_id is not None:
            q = q.where(StockLevel.batch_id == batch_id)
        else:
            q = q.where(StockLevel.batch_id.is_(None))
        if variant_id is not None:
            q = q.where(StockLevel.variant_id == variant_id)
        else:
            q = q.where(StockLevel.variant_id.is_(None))
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def list_levels(
        self,
        tenant_id: str,
        product_id: str | None = None,
        warehouse_id: str | None = None,
        variant_id: str | None = None,
        location_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StockLevel], int]:
        base = select(StockLevel).where(
            StockLevel.tenant_id == tenant_id, StockLevel.qty_on_hand > 0,
        )
        if product_id:
            base = base.where(StockLevel.product_id == product_id)
        if warehouse_id:
            base = base.where(StockLevel.warehouse_id == warehouse_id)
        if variant_id:
            base = base.where(StockLevel.variant_id == variant_id)
        if location_id:
            base = base.where(StockLevel.location_id == location_id)

        from sqlalchemy import func as fn
        count_q = select(fn.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            base
            .options(joinedload(StockLevel.product), joinedload(StockLevel.warehouse), joinedload(StockLevel.location))
            .order_by(StockLevel.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(q)
        return list(result.scalars().unique().all()), total

    async def assign_location(
        self,
        level_id: str,
        tenant_id: str,
        location_id: str | None,
    ) -> StockLevel | None:
        """Assign or clear the location on a stock level."""
        result = await self.db.execute(
            select(StockLevel)
            .options(joinedload(StockLevel.product), joinedload(StockLevel.warehouse), joinedload(StockLevel.location))
            .where(
                StockLevel.id == level_id,
                StockLevel.tenant_id == tenant_id,
            )
        )
        level = result.scalar_one_or_none()
        if not level:
            return None
        level.location_id = location_id
        level.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(level)
        return level

    async def list_low_stock(self, tenant_id: str) -> list[StockLevel]:
        """Return StockLevels where qty is at or below the effective reorder point.

        The effective threshold is whichever is greater:
        - StockLevel.reorder_point  (warehouse-level override)
        - Product.reorder_point     (product-level default)
        - Product.min_stock_level   (minimum stock threshold)
        At least one of them must be > 0 for a product to be eligible.
        """
        from sqlalchemy import case, func as fn

        effective_threshold = case(
            # If warehouse-level override is set, use it
            (StockLevel.reorder_point > 0, StockLevel.reorder_point),
            # Otherwise fall back to whichever product-level field is greater
            else_=case(
                (Product.reorder_point > Product.min_stock_level, Product.reorder_point),
                else_=Product.min_stock_level,
            ),
        )

        # Use available stock (on_hand - reserved) for threshold comparison
        available_qty = StockLevel.qty_on_hand - fn.coalesce(StockLevel.qty_reserved, 0)

        result = await self.db.execute(
            select(StockLevel)
            .join(Product, StockLevel.product_id == Product.id)
            .options(joinedload(StockLevel.product), joinedload(StockLevel.warehouse), joinedload(StockLevel.location))
            .where(
                StockLevel.tenant_id == tenant_id,
                available_qty <= effective_threshold,
                # At least one threshold must be configured
                (StockLevel.reorder_point > 0) |
                (Product.reorder_point > 0) |
                (Product.min_stock_level > 0),
                Product.is_active == True,  # noqa: E712
            )
            .order_by(available_qty)
        )
        return list(result.scalars().unique().all())

    async def _get_level_for_update(
        self,
        product_id: str,
        warehouse_id: str,
        batch_id: str | None = None,
        variant_id: str | None = None,
        location_id: str | None = None,
    ) -> StockLevel | None:
        """Same as get_level but takes a SELECT FOR UPDATE row lock.
        Use this whenever the caller will mutate qty_on_hand / qty_reserved.
        """
        q = select(StockLevel).where(
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
        )
        if batch_id is not None:
            q = q.where(StockLevel.batch_id == batch_id)
        else:
            q = q.where(StockLevel.batch_id.is_(None))
        if variant_id is not None:
            q = q.where(StockLevel.variant_id == variant_id)
        else:
            q = q.where(StockLevel.variant_id.is_(None))
        if location_id is not None:
            q = q.where(StockLevel.location_id == location_id)
        q = q.with_for_update()
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def upsert_level(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        delta: Decimal,
        batch_id: str | None = None,
        unit_cost: Decimal | None = None,
        variant_id: str | None = None,
        location_id: str | None = None,
    ) -> StockLevel | None:
        # Take a row-level lock if the level exists; the lock prevents concurrent
        # writers from causing lost updates on qty_on_hand / weighted_avg_cost.
        level = await self._get_level_for_update(
            product_id, warehouse_id, batch_id, variant_id, location_id,
        )
        # _get_level_for_update already includes location_id in the WHERE clause
        if level is None:
            if delta <= 0:
                return None
            # Inherit reorder_point from Product when creating a new StockLevel
            prod_result = await self.db.execute(
                select(Product.reorder_point, Product.min_stock_level)
                .where(Product.id == product_id)
            )
            prod_row = prod_result.first()
            inherited_rp = 0
            if prod_row:
                inherited_rp = max(prod_row.reorder_point or 0, prod_row.min_stock_level or 0)

            level = StockLevel(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                batch_id=batch_id,
                variant_id=variant_id,
                location_id=location_id,
                qty_on_hand=max(Decimal("0"), delta),
                qty_reserved=Decimal("0"),
                weighted_avg_cost=unit_cost,
                reorder_point=inherited_rp,
            )
            self.db.add(level)
        else:
            # Update weighted average cost on inflow
            if delta > 0 and unit_cost is not None:
                old_qty = level.qty_on_hand
                old_cost = level.weighted_avg_cost or Decimal("0")
                new_qty = old_qty + delta
                if new_qty > 0:
                    level.weighted_avg_cost = (
                        (old_qty * old_cost + delta * unit_cost) / new_qty
                    )
            new_qty = level.qty_on_hand + delta
            level.qty_on_hand = max(Decimal("0"), new_qty)
            level.updated_at = datetime.now(timezone.utc)
            # Remove record if stock is zero and nothing is reserved
            if level.qty_on_hand <= 0 and level.qty_reserved <= 0:
                await self.db.delete(level)
                await self.db.flush()
                return None
        await self.db.flush()
        await self.db.refresh(level)
        return level

    async def reserve(
        self,
        product_id: str,
        warehouse_id: str,
        qty: Decimal,
        variant_id: str | None = None,
        batch_id: str | None = None,
        location_id: str | None = None,
    ) -> StockLevel | None:
        """Atomically reserve stock. Uses an UPDATE … WHERE qty_on_hand - qty_reserved >= qty
        statement so two concurrent reservations cannot oversell.

        Filters by batch_id and location_id (when provided, or NULL otherwise)
        so a product+warehouse with multiple batches/locations doesn't get
        ALL its rows incremented at once.
        """
        from sqlalchemy import update as _update
        now = datetime.now(timezone.utc)

        conditions = [
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
            (StockLevel.qty_on_hand - StockLevel.qty_reserved) >= qty,
        ]
        if variant_id is not None:
            conditions.append(StockLevel.variant_id == variant_id)
        else:
            conditions.append(StockLevel.variant_id.is_(None))
        if batch_id is not None:
            conditions.append(StockLevel.batch_id == batch_id)
        else:
            conditions.append(StockLevel.batch_id.is_(None))
        if location_id is not None:
            conditions.append(StockLevel.location_id == location_id)
        else:
            conditions.append(StockLevel.location_id.is_(None))

        stmt = (
            _update(StockLevel)
            .where(*conditions)
            .values(
                qty_reserved=StockLevel.qty_reserved + qty,
                updated_at=now,
            )
            .returning(StockLevel.id)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if row is None:
            level = await self.get_level(product_id, warehouse_id, batch_id, variant_id)
            if not level:
                raise ValueError(
                    f"No stock level for product {product_id} in warehouse {warehouse_id}"
                )
            available = level.qty_on_hand - level.qty_reserved
            raise ValueError(
                f"Insufficient available stock: {available} available, {qty} requested"
            )
        await self.db.flush()
        return await self.get_level(product_id, warehouse_id, batch_id, variant_id)

    async def release_reservation(
        self,
        product_id: str,
        warehouse_id: str,
        qty: Decimal,
        variant_id: str | None = None,
        batch_id: str | None = None,
        location_id: str | None = None,
    ) -> StockLevel | None:
        """Atomically release a reservation. Refuses to underflow qty_reserved."""
        from sqlalchemy import update as _update
        now = datetime.now(timezone.utc)

        conditions = [
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.qty_reserved >= qty,
        ]
        if variant_id is not None:
            conditions.append(StockLevel.variant_id == variant_id)
        else:
            conditions.append(StockLevel.variant_id.is_(None))
        if batch_id is not None:
            conditions.append(StockLevel.batch_id == batch_id)
        else:
            conditions.append(StockLevel.batch_id.is_(None))
        if location_id is not None:
            conditions.append(StockLevel.location_id == location_id)
        else:
            conditions.append(StockLevel.location_id.is_(None))

        stmt = (
            _update(StockLevel)
            .where(*conditions)
            .values(
                qty_reserved=StockLevel.qty_reserved - qty,
                updated_at=now,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return await self.get_level(product_id, warehouse_id, batch_id, variant_id)

    async def get_available_stock(self, tenant_id: str, product_id: str, warehouse_id: str | None = None):
        """Get stock availability summary: on_hand, reserved, available, in_transit."""
        from sqlalchemy import func as sa_func
        q = (
            select(
                sa_func.coalesce(sa_func.sum(StockLevel.qty_on_hand), 0).label("qty_on_hand"),
                sa_func.coalesce(sa_func.sum(StockLevel.qty_reserved), 0).label("qty_reserved"),
                sa_func.coalesce(sa_func.sum(StockLevel.qty_in_transit), 0).label("qty_in_transit"),
            )
            .where(StockLevel.tenant_id == tenant_id, StockLevel.product_id == product_id)
        )
        if warehouse_id:
            q = q.where(StockLevel.warehouse_id == warehouse_id)
        row = (await self.db.execute(q)).one()
        on_hand = row.qty_on_hand
        reserved = row.qty_reserved
        in_transit = row.qty_in_transit
        return {
            "qty_on_hand": float(on_hand),
            "qty_reserved": float(reserved),
            "qty_available": float(on_hand - reserved),
            "qty_in_transit": float(in_transit),
        }

    async def set_qty(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        new_qty: Decimal,
        batch_id: str | None = None,
        variant_id: str | None = None,
    ) -> StockLevel | None:
        level = await self.get_level(product_id, warehouse_id, batch_id, variant_id)
        if level is None:
            if new_qty <= 0:
                return None
            level = StockLevel(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                batch_id=batch_id,
                variant_id=variant_id,
                qty_on_hand=max(Decimal("0"), new_qty),
                qty_reserved=Decimal("0"),
            )
            self.db.add(level)
        else:
            level.qty_on_hand = max(Decimal("0"), new_qty)
            level.updated_at = datetime.now(timezone.utc)
            # Remove record if stock is zero and nothing is reserved
            if level.qty_on_hand <= 0 and level.qty_reserved <= 0:
                await self.db.delete(level)
                await self.db.flush()
                return None
        await self.db.flush()
        await self.db.refresh(level)
        return level
