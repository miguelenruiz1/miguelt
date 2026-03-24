"""Analytics / overview aggregations for inventory."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MovementType, POStatus, Product, ProductType, PurchaseOrder, StockLevel, StockMovement, Supplier, SupplierType, Warehouse, WarehouseLocation
from app.repositories.batch_repo import BatchRepository
from app.repositories.cycle_count_repo import CycleCountRepository
from app.repositories.event_repo import InventoryEventRepository
from app.repositories.production_repo import ProductionRunRepository
from app.repositories.stock_repo import StockRepository
from app.services.stock_service import StockService


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.stock_service = StockService(db)
        self.stock_repo = StockRepository(db)
        self.cc_repo = CycleCountRepository(db)
        self.event_repo = InventoryEventRepository(db)
        self.batch_repo = BatchRepository(db)
        self.production_repo = ProductionRunRepository(db)

    async def overview(self, tenant_id: str) -> dict:
        summary = await self.stock_service.get_summary(tenant_id)

        # Pending POs
        result = await self.db.execute(
            select(func.count()).where(
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.status.in_([POStatus.draft, POStatus.sent, POStatus.confirmed, POStatus.partial]),
            )
        )
        pending_pos = result.scalar_one()

        # Top 10 products by movement count (last 30 days)
        since = datetime.now(timezone.utc) - timedelta(days=30)
        top_q = (
            select(
                StockMovement.product_id,
                func.count().label("movement_count"),
            )
            .where(
                StockMovement.tenant_id == tenant_id,
                StockMovement.created_at >= since,
            )
            .group_by(StockMovement.product_id)
            .order_by(func.count().desc())
            .limit(10)
        )
        top_result = await self.db.execute(top_q)
        top_rows = top_result.fetchall()

        # Batch-load products for top rows
        top_product_ids = [row.product_id for row in top_rows]
        if top_product_ids:
            prod_result = await self.db.execute(
                select(Product).where(Product.id.in_(top_product_ids))
            )
            prod_map = {p.id: p for p in prod_result.scalars().all()}
        else:
            prod_map = {}

        top_products = []
        for row in top_rows:
            prod = prod_map.get(row.product_id)
            if prod:
                top_products.append({
                    "product_id": row.product_id,
                    "sku": prod.sku,
                    "name": prod.name,
                    "movement_count": row.movement_count,
                })

        # Low stock alerts
        low_stock_levels = await self.stock_repo.list_low_stock(tenant_id)
        alerts = []
        for sl in low_stock_levels:
            effective_rp = sl.reorder_point
            if effective_rp <= 0 and sl.product:
                effective_rp = max(sl.product.reorder_point or 0, sl.product.min_stock_level or 0)
            qty_reserved = float(sl.qty_reserved) if sl.qty_reserved else 0
            qty_available = float(sl.qty_on_hand) - qty_reserved
            alerts.append({
                "product_id": sl.product_id,
                "sku": sl.product.sku if sl.product else None,
                "product_name": sl.product.name if sl.product else None,
                "warehouse_id": sl.warehouse_id,
                "warehouse_name": sl.warehouse.name if sl.warehouse else None,
                "qty_on_hand": float(sl.qty_on_hand),
                "qty_reserved": qty_reserved,
                "qty_available": qty_available,
                "reorder_point": effective_rp,
            })

        # Movement trend: daily counts for last 30 days
        trend_q = (
            select(
                func.date(StockMovement.created_at).label("day"),
                func.count().label("count"),
            )
            .where(
                StockMovement.tenant_id == tenant_id,
                StockMovement.created_at >= since,
            )
            .group_by(func.date(StockMovement.created_at))
            .order_by(func.date(StockMovement.created_at))
        )
        trend_result = await self.db.execute(trend_q)
        movement_trend = [
            {"date": str(row.day), "count": row.count}
            for row in trend_result.fetchall()
        ]

        # Movements by type (last 30 days)
        by_type_q = (
            select(
                StockMovement.movement_type,
                func.count().label("count"),
            )
            .where(
                StockMovement.tenant_id == tenant_id,
                StockMovement.created_at >= since,
            )
            .group_by(StockMovement.movement_type)
            .order_by(func.count().desc())
        )
        by_type_result = await self.db.execute(by_type_q)
        movements_by_type = [
            {"type": row.movement_type, "count": row.count}
            for row in by_type_result.fetchall()
        ]

        # Product type breakdown (count of active products per active type)
        pt_q = (
            select(
                ProductType.id,
                ProductType.name,
                ProductType.color,
                func.count(Product.id).label("product_count"),
            )
            .join(Product, (Product.product_type_id == ProductType.id) & (Product.is_active == True), isouter=True)  # noqa: E712
            .where(
                ProductType.tenant_id == tenant_id,
                ProductType.is_active == True,  # noqa: E712
            )
            .group_by(ProductType.id, ProductType.name, ProductType.color)
            .order_by(func.count(Product.id).desc())
        )
        pt_result = await self.db.execute(pt_q)
        product_type_breakdown = [
            {"id": row.id, "name": row.name, "color": row.color, "count": row.product_count}
            for row in pt_result.fetchall()
        ]

        # Count products without a product type assigned
        untyped_result = await self.db.execute(
            select(func.count()).where(
                Product.tenant_id == tenant_id,
                Product.is_active == True,  # noqa: E712
                Product.product_type_id.is_(None),
            )
        )
        untyped_count = untyped_result.scalar_one()
        if untyped_count > 0:
            product_type_breakdown.append({
                "id": "__untyped__",
                "name": "Sin tipo",
                "color": "#94a3b8",
                "count": untyped_count,
            })

        # Supplier type breakdown (count of active suppliers per active type)
        st_q = (
            select(
                SupplierType.id,
                SupplierType.name,
                SupplierType.color,
                func.count(Supplier.id).label("supplier_count"),
            )
            .join(Supplier, (Supplier.supplier_type_id == SupplierType.id) & (Supplier.is_active == True), isouter=True)  # noqa: E712
            .where(
                SupplierType.tenant_id == tenant_id,
                SupplierType.is_active == True,  # noqa: E712
            )
            .group_by(SupplierType.id, SupplierType.name, SupplierType.color)
            .order_by(func.count(Supplier.id).desc())
        )
        st_result = await self.db.execute(st_q)
        supplier_type_breakdown = [
            {"id": row.id, "name": row.name, "color": row.color, "count": row.supplier_count}
            for row in st_result.fetchall()
        ]

        # Count suppliers without a supplier type assigned
        untyped_sup_result = await self.db.execute(
            select(func.count()).where(
                Supplier.tenant_id == tenant_id,
                Supplier.is_active == True,  # noqa: E712
                Supplier.supplier_type_id.is_(None),
            )
        )
        untyped_sup_count = untyped_sup_result.scalar_one()
        if untyped_sup_count > 0:
            supplier_type_breakdown.append({
                "id": "__untyped__",
                "name": "Sin tipo",
                "color": "#94a3b8",
                "count": untyped_sup_count,
            })

        # Cycle count metrics
        latest_ira = await self.cc_repo.latest_ira(tenant_id)
        pending_cycle_counts = await self.cc_repo.count_pending(tenant_id)

        # Event summary, expiring batches, production runs
        event_summary = await self.event_repo.count_by_severity(tenant_id)
        event_type_summary = await self.event_repo.count_by_type(tenant_id)
        expiring_batches_count = await self.batch_repo.count_expiring(tenant_id, 30)
        production_runs_this_month = await self.production_repo.count_this_month(tenant_id)

        return {
            **summary,
            "pending_pos": pending_pos,
            "top_products": top_products,
            "low_stock_alerts": alerts,
            "movement_trend": movement_trend,
            "movements_by_type": movements_by_type,
            "product_type_breakdown": product_type_breakdown,
            "supplier_type_breakdown": supplier_type_breakdown,
            "event_summary": event_summary,
            "event_type_summary": event_type_summary,
            "expiring_batches_count": expiring_batches_count,
            "production_runs_this_month": production_runs_this_month,
            "latest_ira": latest_ira,
            "pending_cycle_counts": pending_cycle_counts,
        }

    async def occupation(self, tenant_id: str, warehouse_id: str | None = None) -> dict:
        """Calculate warehouse occupation KPIs.

        Two modes:
        - If warehouses have WarehouseLocation records: measure by location occupancy
        - Otherwise: measure by distinct products with stock per warehouse
        """
        # ── Get all active warehouses ───────────────────────────────────
        wh_q = select(Warehouse).where(
            Warehouse.tenant_id == tenant_id,
            Warehouse.is_active == True,  # noqa: E712
        )
        if warehouse_id:
            wh_q = wh_q.where(Warehouse.id == warehouse_id)
        wh_result = await self.db.execute(wh_q)
        warehouses = list(wh_result.scalars().all())

        # ── Get all active locations ────────────────────────────────────
        loc_q = select(WarehouseLocation).where(
            WarehouseLocation.tenant_id == tenant_id,
            WarehouseLocation.is_active == True,  # noqa: E712
        )
        if warehouse_id:
            loc_q = loc_q.where(WarehouseLocation.warehouse_id == warehouse_id)
        loc_result = await self.db.execute(loc_q)
        all_locations = list(loc_result.scalars().all())
        has_locations = len(all_locations) > 0

        # ── Stock levels with qty > 0 ──────────────────────────────────
        stock_q = select(StockLevel).where(
            StockLevel.tenant_id == tenant_id,
            StockLevel.qty_on_hand > 0,
        )
        if warehouse_id:
            stock_q = stock_q.where(StockLevel.warehouse_id == warehouse_id)
        stock_result = await self.db.execute(stock_q)
        all_stock = list(stock_result.scalars().all())

        # ── Compute per-warehouse breakdown ─────────────────────────────
        by_warehouse: list[dict] = []

        if has_locations:
            # MODE A: location-based occupancy
            occupied_location_ids = {sl.location_id for sl in all_stock if sl.location_id}

            total_locations = len(all_locations)
            occupied_locations = sum(1 for loc in all_locations if loc.id in occupied_location_ids)
            free_locations = total_locations - occupied_locations
            occupation_pct = (occupied_locations / total_locations * 100) if total_locations > 0 else 0.0

            # By type breakdown
            by_type: dict[str, dict] = {}
            for loc in all_locations:
                lt = loc.location_type or "unknown"
                if lt not in by_type:
                    by_type[lt] = {"total": 0, "occupied": 0}
                by_type[lt]["total"] += 1
                if loc.id in occupied_location_ids:
                    by_type[lt]["occupied"] += 1

            if not warehouse_id:
                for wh in warehouses:
                    wh_locs = [loc for loc in all_locations if loc.warehouse_id == wh.id]
                    wh_total = len(wh_locs)
                    wh_occupied = sum(1 for loc in wh_locs if loc.id in occupied_location_ids)
                    by_warehouse.append({
                        "warehouse_id": wh.id,
                        "warehouse_name": wh.name,
                        "total_locations": wh_total,
                        "occupied_locations": wh_occupied,
                        "free_locations": wh_total - wh_occupied,
                        "occupation_pct": round((wh_occupied / wh_total * 100) if wh_total > 0 else 0.0, 2),
                    })
        else:
            # MODE B: qty-based occupancy (no locations configured)
            # Per warehouse: sum qty_on_hand across all stock levels.
            # If warehouse has max_stock_capacity → use that as denominator for %.
            # If not → no percentage, just show total quantity.
            by_type = {}

            # Build per-warehouse total qty_on_hand
            wh_product_counts: dict[str, float] = {wh.id: 0.0 for wh in warehouses}
            for sl in all_stock:
                if sl.warehouse_id in wh_product_counts:
                    wh_product_counts[sl.warehouse_id] += float(sl.qty_on_hand)

            total_cap = 0
            total_used = 0
            for wh in warehouses:
                wh_used = round(wh_product_counts.get(wh.id, 0.0), 2)
                cap = getattr(wh, "max_stock_capacity", None)
                has_cap = cap is not None and cap > 0

                if has_cap:
                    wh_cap = int(cap)
                    pct = round((wh_used / wh_cap * 100) if wh_cap > 0 else 0.0, 2)
                    total_cap += wh_cap
                    total_used += wh_used
                else:
                    wh_cap = wh_used  # no cap → show used as total
                    pct = 0.0
                    total_cap += wh_used
                    total_used += wh_used

                if not warehouse_id:
                    by_warehouse.append({
                        "warehouse_id": wh.id,
                        "warehouse_name": wh.name,
                        "total_locations": wh_cap,
                        "occupied_locations": wh_used,
                        "free_locations": max(wh_cap - wh_used, 0) if has_cap else 0,
                        "occupation_pct": pct,
                        "has_capacity": has_cap,
                    })

            total_locations = total_cap if total_cap > 0 else len(warehouses)
            occupied_locations = total_used
            free_locations = max(total_locations - occupied_locations, 0)
            occupation_pct = (occupied_locations / total_locations * 100) if total_locations > 0 else 0.0

        # ── Stale stock: products with no movement in last 180 days ─────
        since_180 = datetime.now(timezone.utc) - timedelta(days=180)
        recent_products_q = (
            select(StockMovement.product_id)
            .where(
                StockMovement.tenant_id == tenant_id,
                StockMovement.created_at >= since_180,
            )
            .distinct()
        )
        stale_q = (
            select(
                StockLevel.product_id,
                func.sum(StockLevel.qty_on_hand).label("total_qty"),
            )
            .where(
                StockLevel.tenant_id == tenant_id,
                StockLevel.qty_on_hand > 0,
                ~StockLevel.product_id.in_(recent_products_q),
            )
            .group_by(StockLevel.product_id)
        )
        if warehouse_id:
            stale_q = stale_q.where(StockLevel.warehouse_id == warehouse_id)

        stale_result = await self.db.execute(stale_q)
        stale_rows = stale_result.fetchall()

        # Batch-load products for stale rows
        stale_product_ids = [row.product_id for row in stale_rows]
        if stale_product_ids:
            stale_prod_result = await self.db.execute(
                select(Product).where(Product.id.in_(stale_product_ids))
            )
            stale_prod_map = {p.id: p for p in stale_prod_result.scalars().all()}
        else:
            stale_prod_map = {}

        stale_stock = []
        for row in stale_rows:
            prod = stale_prod_map.get(row.product_id)
            stale_stock.append({
                "product_id": row.product_id,
                "sku": prod.sku if prod else None,
                "name": prod.name if prod else None,
                "total_qty": float(row.total_qty),
            })

        result = {
            "total_locations": total_locations,
            "occupied_locations": occupied_locations,
            "free_locations": free_locations,
            "occupation_pct": round(occupation_pct, 2),
            "by_type": by_type,
            "stale_stock": stale_stock,
        }
        if not warehouse_id:
            result["by_warehouse"] = by_warehouse
        return result

    async def abc_classification(self, tenant_id: str, months: int = 12) -> dict:
        """Calculate ABC classification based on movement value over last N months."""
        import math
        since = datetime.now(timezone.utc) - timedelta(days=months * 30)

        # Get total movement value per product (qty * unit_cost for outgoing movements)
        q = (
            select(
                StockMovement.product_id,
                func.sum(StockMovement.quantity * func.coalesce(StockMovement.unit_cost, 0)).label("total_value"),
                func.sum(StockMovement.quantity).label("total_qty"),
                func.count().label("movement_count"),
            )
            .where(
                StockMovement.tenant_id == tenant_id,
                StockMovement.created_at >= since,
            )
            .group_by(StockMovement.product_id)
            .order_by(func.sum(StockMovement.quantity * func.coalesce(StockMovement.unit_cost, 0)).desc())
        )
        result = await self.db.execute(q)
        rows = result.fetchall()

        # Calculate cumulative percentages
        grand_total_value = sum(float(r.total_value or 0) for r in rows)
        total_items = len(rows)

        # Batch-load all products for ABC rows
        abc_product_ids = [row.product_id for row in rows]
        if abc_product_ids:
            abc_prod_result = await self.db.execute(
                select(Product).where(Product.id.in_(abc_product_ids))
            )
            abc_prod_map = {p.id: p for p in abc_prod_result.scalars().all()}
        else:
            abc_prod_map = {}

        items = []
        cumulative_value = 0.0
        for i, row in enumerate(rows):
            val = float(row.total_value or 0)
            cumulative_value += val
            value_pct = (val / grand_total_value * 100) if grand_total_value > 0 else 0
            cumulative_pct = (cumulative_value / grand_total_value * 100) if grand_total_value > 0 else 0
            item_pct = ((i + 1) / total_items * 100) if total_items > 0 else 0

            # Classify: A = cumulative <= 80%, B = 80-95%, C = 95-100%
            if cumulative_pct <= 80:
                abc_class = "A"
            elif cumulative_pct <= 95:
                abc_class = "B"
            else:
                abc_class = "C"

            prod = abc_prod_map.get(row.product_id)

            items.append({
                "product_id": row.product_id,
                "sku": prod.sku if prod else None,
                "name": prod.name if prod else None,
                "total_value": round(val, 2),
                "total_qty": float(row.total_qty),
                "movement_count": row.movement_count,
                "value_pct": round(value_pct, 2),
                "cumulative_pct": round(cumulative_pct, 2),
                "abc_class": abc_class,
            })

        # Summary counts
        a_count = sum(1 for it in items if it["abc_class"] == "A")
        b_count = sum(1 for it in items if it["abc_class"] == "B")
        c_count = sum(1 for it in items if it["abc_class"] == "C")
        a_value = sum(it["total_value"] for it in items if it["abc_class"] == "A")
        b_value = sum(it["total_value"] for it in items if it["abc_class"] == "B")
        c_value = sum(it["total_value"] for it in items if it["abc_class"] == "C")

        return {
            "period_months": months,
            "total_products": total_items,
            "grand_total_value": round(grand_total_value, 2),
            "summary": {
                "A": {"count": a_count, "value": round(a_value, 2), "value_pct": round(a_value / grand_total_value * 100, 2) if grand_total_value else 0},
                "B": {"count": b_count, "value": round(b_value, 2), "value_pct": round(b_value / grand_total_value * 100, 2) if grand_total_value else 0},
                "C": {"count": c_count, "value": round(c_value, 2), "value_pct": round(c_value / grand_total_value * 100, 2) if grand_total_value else 0},
            },
            "items": items,
        }

    async def eoq(self, tenant_id: str, ordering_cost: float, holding_cost_pct: float) -> dict:
        """Calculate Economic Order Quantity for each product with movement history."""
        import math
        since = datetime.now(timezone.utc) - timedelta(days=365)

        # Annual demand per product (sum of issue/sale quantities in last 12 months)
        q = (
            select(
                StockMovement.product_id,
                func.sum(StockMovement.quantity).label("annual_demand"),
            )
            .where(
                StockMovement.tenant_id == tenant_id,
                StockMovement.created_at >= since,
                StockMovement.movement_type.in_([
                    MovementType.sale, MovementType.adjustment_out,
                    MovementType.transfer, MovementType.waste,
                ]),
            )
            .group_by(StockMovement.product_id)
        )
        result = await self.db.execute(q)
        rows = result.fetchall()

        # Batch-load all products for EOQ rows
        eoq_product_ids = [row.product_id for row in rows]
        if eoq_product_ids:
            eoq_prod_result = await self.db.execute(
                select(Product).where(Product.id.in_(eoq_product_ids))
            )
            eoq_prod_map = {p.id: p for p in eoq_prod_result.scalars().all()}
        else:
            eoq_prod_map = {}

        items = []
        for row in rows:
            demand = float(row.annual_demand)
            if demand <= 0:
                continue

            prod = eoq_prod_map.get(row.product_id)
            if not prod or not prod.last_purchase_cost:
                continue

            unit_cost = float(prod.last_purchase_cost)
            holding_cost = unit_cost * (holding_cost_pct / 100)

            if holding_cost <= 0:
                continue

            eoq_val = math.sqrt((2 * demand * ordering_cost) / holding_cost)
            orders_per_year = demand / eoq_val if eoq_val > 0 else 0
            total_ordering_cost = orders_per_year * ordering_cost
            total_holding_cost = (eoq_val / 2) * holding_cost
            total_cost = total_ordering_cost + total_holding_cost

            items.append({
                "product_id": row.product_id,
                "sku": prod.sku,
                "name": prod.name,
                "annual_demand": round(demand, 2),
                "unit_cost": unit_cost,
                "eoq": round(eoq_val, 0),
                "current_reorder_qty": prod.reorder_quantity,
                "orders_per_year": round(orders_per_year, 1),
                "total_annual_cost": round(total_cost, 2),
            })

        items.sort(key=lambda x: x["annual_demand"], reverse=True)

        return {
            "ordering_cost": ordering_cost,
            "holding_cost_pct": holding_cost_pct,
            "total_products": len(items),
            "items": items,
        }

    async def stock_policy(self, tenant_id: str) -> dict:
        """Check rotation compliance vs product type target months."""
        since_12m = datetime.now(timezone.utc) - timedelta(days=365)

        # Get product types with rotation target
        pt_result = await self.db.execute(
            select(ProductType).where(
                ProductType.tenant_id == tenant_id,
                ProductType.is_active == True,  # noqa: E712
                ProductType.rotation_target_months.isnot(None),
            )
        )
        product_types = list(pt_result.scalars().all())

        items = []
        for pt in product_types:
            target_months = pt.rotation_target_months
            if not target_months or target_months <= 0:
                continue

            # Current stock value for products of this type
            stock_q = (
                select(func.sum(StockLevel.qty_on_hand * func.coalesce(StockLevel.weighted_avg_cost, 0)))
                .where(
                    StockLevel.tenant_id == tenant_id,
                    StockLevel.product_id.in_(
                        select(Product.id).where(Product.product_type_id == pt.id)
                    ),
                    StockLevel.qty_on_hand > 0,
                )
            )
            stock_result = await self.db.execute(stock_q)
            current_stock_value = float(stock_result.scalar_one() or 0)

            # Monthly consumption (outgoing movements value in last 12 months / 12)
            consumption_q = (
                select(func.sum(StockMovement.quantity * func.coalesce(StockMovement.unit_cost, 0)))
                .join(Product, Product.id == StockMovement.product_id)
                .where(
                    StockMovement.tenant_id == tenant_id,
                    Product.product_type_id == pt.id,
                    StockMovement.created_at >= since_12m,
                    StockMovement.movement_type.in_([
                        MovementType.sale, MovementType.adjustment_out, MovementType.waste,
                    ]),
                )
            )
            consumption_result = await self.db.execute(consumption_q)
            annual_consumption = float(consumption_result.scalar_one() or 0)
            monthly_consumption = annual_consumption / 12 if annual_consumption > 0 else 0

            # Calculate months of stock on hand
            months_on_hand = (current_stock_value / monthly_consumption) if monthly_consumption > 0 else None

            # Compliance
            if months_on_hand is None:
                status = "no_data"
            elif months_on_hand <= target_months:
                status = "ok"
            else:
                status = "excess"

            items.append({
                "product_type_id": pt.id,
                "product_type_name": pt.name,
                "color": pt.color,
                "target_months": target_months,
                "current_stock_value": round(current_stock_value, 2),
                "monthly_consumption": round(monthly_consumption, 2),
                "months_on_hand": round(months_on_hand, 1) if months_on_hand is not None else None,
                "status": status,
            })

        return {"items": items}

    async def storage_valuation(self, tenant_id: str) -> dict:
        """Calculate storage cost per warehouse based on cost_per_sqm and area."""
        wh_result = await self.db.execute(
            select(Warehouse).where(
                Warehouse.tenant_id == tenant_id,
                Warehouse.is_active == True,  # noqa: E712
            )
        )
        warehouses = list(wh_result.scalars().all())

        items = []
        total_monthly_cost = 0.0
        total_stock_value = 0.0

        for wh in warehouses:
            cost_sqm = float(wh.cost_per_sqm) if wh.cost_per_sqm else None
            area = float(wh.total_area_sqm) if wh.total_area_sqm else None
            monthly_cost = (cost_sqm * area) if (cost_sqm and area) else None

            # Stock value in this warehouse
            sv_result = await self.db.execute(
                select(func.sum(StockLevel.qty_on_hand * func.coalesce(StockLevel.weighted_avg_cost, 0)))
                .where(
                    StockLevel.tenant_id == tenant_id,
                    StockLevel.warehouse_id == wh.id,
                    StockLevel.qty_on_hand > 0,
                )
            )
            stock_value = float(sv_result.scalar_one() or 0)
            total_stock_value += stock_value

            # Location count
            loc_result = await self.db.execute(
                select(func.count()).where(
                    WarehouseLocation.warehouse_id == wh.id,
                    WarehouseLocation.is_active == True,  # noqa: E712
                )
            )
            loc_count = loc_result.scalar_one()

            cost_per_location = (monthly_cost / loc_count) if (monthly_cost and loc_count > 0) else None
            storage_pct = (monthly_cost / stock_value * 100) if (monthly_cost and stock_value > 0) else None

            if monthly_cost:
                total_monthly_cost += monthly_cost

            items.append({
                "warehouse_id": wh.id,
                "warehouse_name": wh.name,
                "cost_per_sqm": cost_sqm,
                "total_area_sqm": area,
                "monthly_cost": round(monthly_cost, 2) if monthly_cost else None,
                "stock_value": round(stock_value, 2),
                "location_count": loc_count,
                "cost_per_location": round(cost_per_location, 2) if cost_per_location else None,
                "storage_cost_pct": round(storage_pct, 2) if storage_pct else None,
            })

        return {
            "total_monthly_cost": round(total_monthly_cost, 2),
            "total_stock_value": round(total_stock_value, 2),
            "storage_to_value_pct": round(total_monthly_cost / total_stock_value * 100, 2) if total_stock_value > 0 else None,
            "items": items,
        }
