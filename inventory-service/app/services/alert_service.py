"""Business logic for stock alerts — auto-generate on low/out-of-stock and expiry."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Product, StockAlert, StockLevel
from app.db.models.tracking import EntityBatch
from app.repositories.alert_repo import AlertRepository
from app.repositories.batch_repo import BatchRepository


class AlertService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AlertRepository(db)
        self.batch_repo = BatchRepository(db)

    async def list_alerts(self, tenant_id: str, **kwargs):
        return await self.repo.list(tenant_id, **kwargs)

    async def mark_read(self, alert_id: str, tenant_id: str):
        return await self.repo.mark_read(alert_id, tenant_id)

    async def resolve(self, alert_id: str, tenant_id: str):
        return await self.repo.resolve(alert_id, tenant_id)

    async def count_unread(self, tenant_id: str):
        return await self.repo.count_unread(tenant_id)

    async def check_and_generate(self, tenant_id: str) -> list[dict]:
        """Scan stock levels and generate alerts for products below thresholds.

        Works per-warehouse: a product can be OK in one warehouse but low in another.
        Uses effective threshold: max(StockLevel.reorder_point, Product.reorder_point, Product.min_stock_level).
        Also detects products with thresholds configured but NO stock records at all.
        """
        from sqlalchemy.orm import joinedload

        # 1) Per-warehouse stock levels with product info
        result = await self.db.execute(
            select(StockLevel)
            .options(joinedload(StockLevel.product), joinedload(StockLevel.warehouse))
            .where(StockLevel.tenant_id == tenant_id)
        )
        levels = list(result.scalars().unique().all())

        # 2) Products with thresholds but possibly NO stock levels at all
        products_with_thresholds = await self.db.execute(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.is_active == True,  # noqa: E712
                (Product.min_stock_level > 0) | (Product.reorder_point > 0),
            )
        )
        all_threshold_products = {p.id: p for p in products_with_thresholds.scalars().all()}

        # Track which products have at least one stock level
        products_with_stock = set()

        # 3) Load existing unresolved alerts to avoid duplicates
        existing_result = await self.db.execute(
            select(StockAlert.product_id, StockAlert.alert_type, StockAlert.warehouse_id)
            .where(
                StockAlert.tenant_id == tenant_id,
                StockAlert.is_resolved == False,  # noqa: E712
            )
        )
        existing_alerts = {(r[0], r[1], r[2]) for r in existing_result.all()}

        alerts_created = []

        # 4) Check each stock level per warehouse
        for sl in levels:
            if not sl.product or not sl.product.is_active:
                continue
            products_with_stock.add(sl.product_id)
            product = sl.product
            qty = float(sl.qty_on_hand)
            wh_name = sl.warehouse.name if sl.warehouse else "Bodega"

            # Effective threshold: warehouse override > product-level max
            effective = sl.reorder_point if sl.reorder_point > 0 else max(
                product.reorder_point or 0, product.min_stock_level or 0
            )
            if effective <= 0:
                continue

            if qty == 0:
                key = (product.id, "out_of_stock", sl.warehouse_id)
                if key not in existing_alerts:
                    alert = await self.repo.create({
                        "tenant_id": tenant_id,
                        "product_id": product.id,
                        "warehouse_id": sl.warehouse_id,
                        "alert_type": "out_of_stock",
                        "message": f"'{product.name}' sin stock en {wh_name}",
                        "current_qty": int(qty),
                        "threshold_qty": effective,
                    })
                    alerts_created.append({"id": alert.id, "type": "out_of_stock", "product": product.name})
            elif qty <= effective:
                # Determine if it's a reorder_point alert or low_stock
                min_lvl = product.min_stock_level or 0
                if qty <= min_lvl and min_lvl > 0:
                    alert_type = "low_stock"
                    msg = f"'{product.name}' stock bajo en {wh_name}: {int(qty)} uds (min: {min_lvl})"
                else:
                    alert_type = "reorder_point"
                    msg = f"'{product.name}' punto de reorden en {wh_name}: {int(qty)} uds (reorden: {effective})"
                key = (product.id, alert_type, sl.warehouse_id)
                if key not in existing_alerts:
                    alert = await self.repo.create({
                        "tenant_id": tenant_id,
                        "product_id": product.id,
                        "warehouse_id": sl.warehouse_id,
                        "alert_type": alert_type,
                        "message": msg,
                        "current_qty": int(qty),
                        "threshold_qty": effective,
                    })
                    alerts_created.append({"id": alert.id, "type": alert_type, "product": product.name})

        # 5) Products with thresholds but NO stock records anywhere = out of stock
        for pid, product in all_threshold_products.items():
            if pid in products_with_stock:
                continue
            key = (pid, "out_of_stock", None)
            if key not in existing_alerts:
                threshold = max(product.reorder_point or 0, product.min_stock_level or 0)
                alert = await self.repo.create({
                    "tenant_id": tenant_id,
                    "product_id": pid,
                    "alert_type": "out_of_stock",
                    "message": f"'{product.name}' sin stock en ninguna bodega",
                    "current_qty": 0,
                    "threshold_qty": threshold,
                })
                alerts_created.append({"id": alert.id, "type": "out_of_stock", "product": product.name})

        # 6) Auto-resolve alerts where stock is now above threshold
        resolve_result = await self.db.execute(
            select(StockAlert).where(
                StockAlert.tenant_id == tenant_id,
                StockAlert.is_resolved == False,  # noqa: E712
            )
        )
        unresolved = list(resolve_result.scalars().all())
        for alert in unresolved:
            # Find current stock for this product+warehouse
            if alert.warehouse_id:
                matching = [
                    sl for sl in levels
                    if sl.product_id == alert.product_id and sl.warehouse_id == alert.warehouse_id
                ]
                current_qty = float(matching[0].qty_on_hand) if matching else 0.0
            else:
                # Global alert — sum across all warehouses
                matching = [sl for sl in levels if sl.product_id == alert.product_id]
                current_qty = sum(float(sl.qty_on_hand) for sl in matching)
            if current_qty > alert.threshold_qty:
                await self.repo.resolve(alert.id, tenant_id)

        return alerts_created

    async def check_expiry_alerts(self, tenant_id: str, days: int = 30) -> list[dict]:
        """Scan active batches and create alerts for those expiring within N days.

        Alert types:
          - 'expired': batch expiration_date < today
          - 'expiring_soon': batch expiration_date within N days from today

        Auto-resolves existing expiry alerts for batches that are no longer active.
        """
        now = datetime.now(timezone.utc)
        today = now.date()
        cutoff = today + timedelta(days=days)

        # 1) Active batches with expiration dates that are expired or expiring soon
        result = await self.db.execute(
            select(EntityBatch).where(
                EntityBatch.tenant_id == tenant_id,
                EntityBatch.is_active == True,  # noqa: E712
                EntityBatch.expiration_date != None,  # noqa: E711
                EntityBatch.expiration_date <= cutoff,
            )
        )
        batches = list(result.scalars().all())

        alerts_created: list[dict] = []

        for batch in batches:
            if batch.expiration_date < today:
                alert_type = "expired"
                msg = (
                    f"Lote '{batch.batch_number}' expirado el {batch.expiration_date.isoformat()}"
                )
            else:
                alert_type = "expiring_soon"
                days_left = (batch.expiration_date - today).days
                msg = (
                    f"Lote '{batch.batch_number}' expira en {days_left} día(s) "
                    f"({batch.expiration_date.isoformat()})"
                )

            # Skip if an unresolved alert already exists for this batch + type
            existing = await self.repo.get_expiry_alert(tenant_id, batch.id, alert_type)
            if existing:
                continue

            alert = await self.repo.create({
                "tenant_id": tenant_id,
                "product_id": batch.entity_id,
                "batch_id": batch.id,
                "alert_type": alert_type,
                "message": msg,
                "current_qty": int(batch.quantity),
                "threshold_qty": 0,
            })
            alerts_created.append({
                "id": alert.id,
                "type": alert_type,
                "batch": batch.batch_number,
                "expiration_date": batch.expiration_date.isoformat(),
            })

        # 2) Auto-resolve expiry alerts for batches that are no longer active
        unresolved = (
            (
                await self.db.execute(
                    select(StockAlert).where(
                        StockAlert.tenant_id == tenant_id,
                        StockAlert.is_resolved == False,  # noqa: E712
                        StockAlert.alert_type.in_(["expired", "expiring_soon"]),
                        StockAlert.batch_id != None,  # noqa: E711
                    )
                )
            )
            .scalars()
            .all()
        )
        # Bulk-load all referenced batches in a single query (was N+1 in loop)
        # NOTE: EntityBatch is imported at module level — do NOT re-import here,
        # it creates a local-scope rebind that shadows the module-level name,
        # triggering UnboundLocalError at line 183 because Python pre-marks the
        # name as local for the entire function.
        if unresolved:
            batch_ids = list({a.batch_id for a in unresolved if a.batch_id})
            batches_q = await self.db.execute(
                select(EntityBatch).where(
                    EntityBatch.tenant_id == tenant_id,
                    EntityBatch.id.in_(batch_ids),
                )
            )
            batch_map = {b.id: b for b in batches_q.scalars().all()}
            for alert in unresolved:
                batch = batch_map.get(alert.batch_id)
                if not batch or not batch.is_active:
                    await self.repo.resolve(alert.id, tenant_id)

        return alerts_created

    async def get_kardex(self, tenant_id: str, product_id: str, warehouse_id: str | None = None) -> list[dict]:
        """Return valued movement history (Kardex) for a product."""
        from app.db.models import StockMovement
        from decimal import Decimal

        q = (
            select(StockMovement)
            .where(StockMovement.tenant_id == tenant_id, StockMovement.product_id == product_id)
        )
        if warehouse_id:
            q = q.where(
                (StockMovement.from_warehouse_id == warehouse_id) |
                (StockMovement.to_warehouse_id == warehouse_id)
            )
        q = q.order_by(StockMovement.created_at)
        result = await self.db.execute(q)
        movements = list(result.scalars().all())

        balance = Decimal("0")
        avg_cost = Decimal("0")
        kardex = []
        for m in movements:
            unit_cost = m.unit_cost or Decimal("0")
            qty = m.quantity or Decimal("0")
            delta = Decimal("0")

            mv = m.movement_type.value
            if warehouse_id:
                # Per-warehouse kardex: direction depends on which side of the movement this warehouse is
                if m.to_warehouse_id == warehouse_id and m.from_warehouse_id != warehouse_id:
                    delta = qty  # inflow to this warehouse
                elif m.from_warehouse_id == warehouse_id and m.to_warehouse_id != warehouse_id:
                    delta = -qty  # outflow from this warehouse
                # If both from and to are same warehouse (shouldn't happen), delta stays 0
            else:
                # Global kardex: transfers are internal so net zero; only external movements count
                INFLOWS = ("purchase", "adjustment_in", "return", "production_in")
                OUTFLOWS = ("sale", "adjustment_out", "waste", "production_out")
                if mv in INFLOWS:
                    delta = qty
                elif mv in OUTFLOWS:
                    delta = -qty
                # transfer is net zero globally

            # Update weighted average cost on inflows
            if delta > 0 and unit_cost > 0:
                new_balance = balance + delta
                if new_balance > 0:
                    avg_cost = (balance * avg_cost + delta * unit_cost) / new_balance
            balance += delta
            if balance <= 0:
                balance = Decimal("0")

            kardex.append({
                "movement_id": m.id,
                "date": m.created_at.isoformat() if m.created_at else None,
                "type": mv,
                "reference": m.reference,
                "quantity": float(delta),
                "unit_cost": float(unit_cost),
                "avg_cost": float(avg_cost),
                "balance": float(balance),
                "value": float(balance * avg_cost) if avg_cost else None,
            })

        return kardex
