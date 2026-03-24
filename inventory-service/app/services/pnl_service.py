"""P&L (Profit & Loss) service — per product and full tenant."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Product, StockLevel, StockMovement, Warehouse, SalesOrder, SalesOrderLine
from app.db.models.enums import MovementType
from app.db.models.cost_history import ProductCostHistory
from app.db.models.enums import SalesOrderStatus
from app.db.models.production import StockLayer
from app.services.pricing_engine import PricingEngine


class PnLService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.pricing = PricingEngine(db)

    async def get_product_pnl(self, product_id: str, tenant_id: str, date_from: datetime, date_to: datetime) -> dict:
        product = (await self.db.execute(select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id))).scalar_one_or_none()
        if not product:
            return {}

        purchases_result = await self.db.execute(
            select(ProductCostHistory.received_at, ProductCostHistory.supplier_name, ProductCostHistory.uom_purchased,
                   ProductCostHistory.qty_purchased, ProductCostHistory.qty_in_base_uom, ProductCostHistory.unit_cost_purchased,
                   ProductCostHistory.unit_cost_base_uom, ProductCostHistory.total_cost, ProductCostHistory.purchase_order_id, ProductCostHistory.market_note)
            .where(ProductCostHistory.product_id == product_id, ProductCostHistory.tenant_id == tenant_id,
                   ProductCostHistory.received_at >= date_from, ProductCostHistory.received_at <= date_to)
            .order_by(ProductCostHistory.received_at.desc())
        )
        purchases = [dict(r._mapping) for r in purchases_result.all()]

        sales_result = await self.db.execute(
            select(SalesOrder.order_number, SalesOrder.created_at.label("sale_date"),
                   SalesOrderLine.qty_ordered, SalesOrderLine.qty_shipped, SalesOrderLine.unit_price,
                   SalesOrderLine.line_total, SalesOrderLine.margin_pct)
            .join(SalesOrder, SalesOrderLine.order_id == SalesOrder.id)
            .where(SalesOrderLine.product_id == product_id, SalesOrderLine.tenant_id == tenant_id,
                   SalesOrder.status.in_([SalesOrderStatus.confirmed, SalesOrderStatus.picking, SalesOrderStatus.shipped, SalesOrderStatus.delivered]),
                   SalesOrder.created_at >= date_from, SalesOrder.created_at <= date_to)
            .order_by(SalesOrder.created_at.desc())
        )
        sales = [dict(r._mapping) for r in sales_result.all()]

        stock_result = await self.db.execute(
            select(Warehouse.name.label("warehouse_name"), StockLevel.qty_on_hand, StockLevel.qty_reserved, StockLevel.weighted_avg_cost)
            .join(Warehouse, StockLevel.warehouse_id == Warehouse.id)
            .where(StockLevel.product_id == product_id, StockLevel.tenant_id == tenant_id)
        )
        stock_by_warehouse = []
        for r in stock_result.all():
            qty = r.qty_on_hand or Decimal("0")
            reserved = r.qty_reserved or Decimal("0")
            avg_cost = r.weighted_avg_cost or Decimal("0")
            stock_by_warehouse.append({"warehouse_name": r.warehouse_name, "qty_on_hand": float(qty), "qty_reserved": float(reserved), "qty_available": float(qty - reserved), "avg_cost": float(avg_cost), "total_value": float(qty * avg_cost)})

        total_purchased_qty = sum(Decimal(str(p.get("qty_in_base_uom", 0))) for p in purchases)
        total_purchased_cost = sum(Decimal(str(p.get("total_cost", 0))) for p in purchases)
        total_sold_qty = sum(Decimal(str(s.get("qty_shipped", 0) or s.get("qty_ordered", 0))) for s in sales)
        total_revenue = sum(Decimal(str(s.get("line_total", 0))) for s in sales)

        avg_row = (await self.db.execute(select(func.sum(StockLayer.unit_cost * StockLayer.quantity_remaining), func.sum(StockLayer.quantity_remaining)).where(StockLayer.entity_id == product_id, StockLayer.quantity_remaining > 0))).one()
        current_avg_cost = (avg_row[0] / avg_row[1]) if avg_row[1] and avg_row[1] > 0 else Decimal("0")

        # Use actual COGS from stock movements when available (costing engine)
        sale_movements_result = await self.db.execute(
            select(StockMovement.cost_total)
            .where(
                StockMovement.product_id == product_id,
                StockMovement.tenant_id == tenant_id,
                StockMovement.movement_type == MovementType.sale,
                StockMovement.created_at >= date_from,
                StockMovement.created_at <= date_to,
                StockMovement.cost_total.isnot(None),
            )
        )
        actual_cogs = sum(
            Decimal(str(r[0])) for r in sale_movements_result.all() if r[0] is not None
        )
        if actual_cogs > 0:
            total_cogs = actual_cogs
        else:
            # Fallback to estimated COGS for historical data before costing engine
            total_cogs = total_sold_qty * current_avg_cost
        gross_profit = total_revenue - total_cogs
        gross_margin_pct = (gross_profit / total_revenue * 100) if total_revenue > 0 else Decimal("0")
        stock_current_qty = sum(Decimal(str(s["qty_on_hand"])) for s in stock_by_warehouse)
        stock_current_value = sum(Decimal(str(s["total_value"])) for s in stock_by_warehouse)
        potential_revenue = stock_current_qty * product.suggested_sale_price if product.suggested_sale_price else Decimal("0")

        config = await self.pricing._get_tenant_config(tenant_id)
        margin_target, _, _ = self.pricing.get_product_margins(product, config)
        cost_values = [Decimal(str(p.get("unit_cost_base_uom", 0))) for p in purchases if p.get("unit_cost_base_uom")]
        lowest = min(cost_values) if cost_values else Decimal("0")
        highest = max(cost_values) if cost_values else Decimal("0")
        price_variation = ((highest - lowest) / lowest * 100) if lowest > 0 else Decimal("0")
        supplier_costs: dict[str, list[Decimal]] = {}
        for p in purchases:
            supplier_costs.setdefault(p.get("supplier_name", ""), []).append(Decimal(str(p.get("unit_cost_base_uom", 0))))
        best_supplier, best_avg = "", Decimal("999999999")
        for sn, costs in supplier_costs.items():
            avg = sum(costs) / len(costs)
            if avg < best_avg:
                best_avg, best_supplier = avg, sn

        return {
            "product_id": product.id, "product_name": product.name, "product_sku": product.sku, "unit_of_measure": product.unit_of_measure,
            "purchases": purchases, "sales": sales, "stock_by_warehouse": stock_by_warehouse,
            "summary": {
                "total_purchased_qty": float(total_purchased_qty), "total_purchased_cost": float(total_purchased_cost),
                "total_sold_qty": float(total_sold_qty), "total_revenue": float(total_revenue),
                "total_cogs": float(total_cogs), "gross_profit": float(gross_profit),
                "gross_margin_pct": float(gross_margin_pct.quantize(Decimal("0.01")) if isinstance(gross_margin_pct, Decimal) else gross_margin_pct),
                "margin_target": float(margin_target), "margin_vs_target": float((gross_margin_pct - margin_target) if isinstance(gross_margin_pct, Decimal) else Decimal(str(gross_margin_pct)) - margin_target),
                "stock_current_qty": float(stock_current_qty), "stock_current_value": float(stock_current_value),
                "potential_revenue": float(potential_revenue), "potential_profit": float(potential_revenue - stock_current_value),
            },
            "market_analysis": {
                "lowest_purchase_cost": float(lowest), "highest_purchase_cost": float(highest),
                "price_variation_pct": float(price_variation), "best_supplier": best_supplier,
                "suggested_price_today": float(product.suggested_sale_price or 0), "minimum_price_today": float(product.minimum_sale_price or 0),
            },
        }

    async def get_full_pnl(self, tenant_id: str, date_from: datetime, date_to: datetime) -> dict:
        products = (await self.db.execute(select(Product).where(Product.tenant_id == tenant_id, Product.is_active == True).order_by(Product.name))).scalars().all()
        product_pnls, totals = [], {"total_purchased_cost": Decimal("0"), "total_revenue": Decimal("0"), "total_cogs": Decimal("0"), "gross_profit": Decimal("0"), "stock_current_value": Decimal("0")}
        for product in products:
            pnl = await self.get_product_pnl(product.id, tenant_id, date_from, date_to)
            if not pnl:
                continue
            s = pnl["summary"]
            if s["total_purchased_cost"] > 0 or s["total_revenue"] > 0 or s["stock_current_value"] > 0:
                product_pnls.append(pnl)
                for k in totals:
                    totals[k] += Decimal(str(s.get(k, 0)))
        product_pnls.sort(key=lambda p: p["summary"]["gross_profit"], reverse=True)
        gm = (totals["gross_profit"] / totals["total_revenue"] * 100) if totals["total_revenue"] > 0 else Decimal("0")
        return {"products": product_pnls, "totals": {k: float(v) for k, v in totals.items()} | {"gross_margin_pct": float(gm), "product_count": len(product_pnls)}}
