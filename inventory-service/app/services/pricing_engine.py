"""Dynamic pricing engine — calculates suggested and minimum prices."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.cost_history import ProductCostHistory
from app.db.models.entity import Product
from app.db.models.production import StockLayer
from app.db.models.sales_order import TenantInventoryConfig


class PricingEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def get_product_margins(self, product: Product, tenant_config: TenantInventoryConfig | None) -> tuple[Decimal, Decimal, str]:
        target = product.margin_target
        minimum = product.margin_minimum
        method = product.margin_cost_method or "last_purchase"
        if target is None:
            target = tenant_config.margin_target_global if tenant_config else Decimal("35.00")
        if minimum is None:
            minimum = tenant_config.margin_minimum_global if tenant_config else Decimal("20.00")
        if method == "last_purchase" and tenant_config and product.margin_cost_method is None:
            method = tenant_config.margin_cost_method_global or "last_purchase"
        return target, minimum, method

    @staticmethod
    def calculate_suggested_price(cost_base_uom: Decimal, margin_target: Decimal) -> Decimal:
        if margin_target >= Decimal("100"):
            return cost_base_uom * Decimal("10")
        divisor = Decimal("1") - margin_target / Decimal("100")
        if divisor <= 0:
            return cost_base_uom * Decimal("10")
        return (cost_base_uom / divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_minimum_price(cost_base_uom: Decimal, margin_minimum: Decimal) -> Decimal:
        if margin_minimum >= Decimal("100"):
            return cost_base_uom * Decimal("10")
        divisor = Decimal("1") - margin_minimum / Decimal("100")
        if divisor <= 0:
            return cost_base_uom * Decimal("10")
        return (cost_base_uom / divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def get_cost_base(self, product_id: str, tenant_id: str, method: str, warehouse_id: str | None = None) -> Decimal | None:
        if method == "last_purchase":
            result = await self.db.execute(select(Product.last_purchase_cost).where(Product.id == product_id, Product.tenant_id == tenant_id))
            return result.scalar_one_or_none()
        if method == "weighted_avg":
            q = select(func.sum(StockLayer.unit_cost * StockLayer.quantity_remaining), func.sum(StockLayer.quantity_remaining)).where(StockLayer.entity_id == product_id, StockLayer.quantity_remaining > 0)
            if warehouse_id:
                q = q.where(StockLayer.warehouse_id == warehouse_id)
            result = await self.db.execute(q)
            row = result.one()
            if row[1] and row[1] > 0:
                return (row[0] / row[1]).quantize(Decimal("0.000001"))
            return None
        if method == "avg_last_3":
            result = await self.db.execute(select(ProductCostHistory.unit_cost_base_uom).where(ProductCostHistory.product_id == product_id, ProductCostHistory.tenant_id == tenant_id).order_by(ProductCostHistory.received_at.desc()).limit(3))
            costs = [row[0] for row in result.all()]
            if costs:
                return (sum(costs) / len(costs)).quantize(Decimal("0.000001"))
            return None
        return None

    async def _get_tenant_config(self, tenant_id: str) -> TenantInventoryConfig | None:
        result = await self.db.execute(select(TenantInventoryConfig).where(TenantInventoryConfig.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def recalculate_product_prices(self, product: Product, tenant_id: str) -> None:
        config = await self._get_tenant_config(tenant_id)
        target, minimum, method = self.get_product_margins(product, config)
        cost_base = await self.get_cost_base(product.id, tenant_id, method)
        if cost_base is None or cost_base <= 0:
            return
        product.suggested_sale_price = self.calculate_suggested_price(cost_base, target)
        product.minimum_sale_price = self.calculate_minimum_price(cost_base, minimum)
        await self.db.flush()

    def validate_sale_price(self, unit_price: Decimal, product: Product, tenant_config: TenantInventoryConfig | None) -> str:
        if product.minimum_sale_price and unit_price < product.minimum_sale_price:
            return "blocked"
        if product.suggested_sale_price and unit_price < product.suggested_sale_price:
            return "warning"
        return "ok"

    async def get_price_for_uom(self, base_price: Decimal, from_uom: str, to_uom: str, tenant_id: str) -> Decimal:
        if from_uom == to_uom:
            return base_price
        from app.services.uom_service import UoMService
        uom_svc = UoMService(self.db)
        factor = await uom_svc.get_conversion_factor(to_uom, from_uom, tenant_id)
        return (base_price * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
