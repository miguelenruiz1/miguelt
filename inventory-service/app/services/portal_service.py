"""Portal (customer self-service) business logic."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.errors import NotFoundError
from app.db.models import Product, SalesOrder, SalesOrderLine, StockLevel
from app.db.models.enums import SalesOrderStatus


class PortalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_customer_stock(self, tenant_id: str, customer_id: str) -> list[dict]:
        """Get stock levels for all products that the customer has ordered."""
        # Find all product_ids from the customer's sales orders
        product_ids_q = (
            select(SalesOrderLine.product_id)
            .join(SalesOrder, SalesOrderLine.order_id == SalesOrder.id)
            .where(
                SalesOrder.tenant_id == tenant_id,
                SalesOrder.customer_id == customer_id,
            )
            .distinct()
        )
        product_ids_result = await self.db.execute(product_ids_q)
        product_ids = [row[0] for row in product_ids_result.fetchall()]

        if not product_ids:
            return []

        # Get stock levels for those products
        q = (
            select(StockLevel)
            .options(joinedload(StockLevel.product), joinedload(StockLevel.warehouse))
            .where(
                StockLevel.tenant_id == tenant_id,
                StockLevel.product_id.in_(product_ids),
                StockLevel.qty_on_hand > 0,
            )
        )
        result = await self.db.execute(q)
        levels = list(result.scalars().unique().all())

        return [
            {
                "product_id": sl.product_id,
                "sku": sl.product.sku if sl.product else None,
                "product_name": sl.product.name if sl.product else None,
                "warehouse_id": sl.warehouse_id,
                "warehouse_name": sl.warehouse.name if sl.warehouse else None,
                "qty_on_hand": float(sl.qty_on_hand),
                "qty_reserved": float(sl.qty_reserved),
                "qc_status": sl.qc_status,
            }
            for sl in levels
        ]

    async def get_customer_orders(
        self,
        tenant_id: str,
        customer_id: str,
        status: str | None = None,
    ) -> list[dict]:
        """List sales orders for a given customer."""
        q = (
            select(SalesOrder)
            .options(joinedload(SalesOrder.lines))
            .where(
                SalesOrder.tenant_id == tenant_id,
                SalesOrder.customer_id == customer_id,
            )
            .order_by(SalesOrder.created_at.desc())
        )
        if status:
            try:
                status_enum = SalesOrderStatus(status)
                q = q.where(SalesOrder.status == status_enum)
            except ValueError:
                pass

        result = await self.db.execute(q)
        orders = list(result.scalars().unique().all())

        return [
            {
                "id": order.id,
                "order_number": order.order_number,
                "status": order.status.value if order.status else None,
                "subtotal": float(order.subtotal),
                "tax_amount": float(order.tax_amount),
                "discount_amount": float(order.discount_amount),
                "total": float(order.total),
                "currency": order.currency,
                "expected_date": order.expected_date.isoformat() if order.expected_date else None,
                "shipped_date": order.shipped_date.isoformat() if order.shipped_date else None,
                "delivered_date": order.delivered_date.isoformat() if order.delivered_date else None,
                "notes": order.notes,
                "line_count": len(order.lines) if order.lines else 0,
                "created_at": order.created_at.isoformat() if order.created_at else None,
            }
            for order in orders
        ]

    async def get_order_detail(
        self,
        tenant_id: str,
        order_id: str,
        customer_id: str,
    ) -> dict:
        """Get a single sales order with lines, scoped to the customer."""
        q = (
            select(SalesOrder)
            .options(
                joinedload(SalesOrder.lines).joinedload(SalesOrderLine.product),
                joinedload(SalesOrder.lines).joinedload(SalesOrderLine.variant),
            )
            .where(
                SalesOrder.id == order_id,
                SalesOrder.tenant_id == tenant_id,
                SalesOrder.customer_id == customer_id,
            )
        )
        result = await self.db.execute(q)
        order = result.scalars().unique().one_or_none()
        if not order:
            raise NotFoundError(f"Order {order_id!r} not found for this customer")

        lines = []
        for line in (order.lines or []):
            lines.append({
                "id": line.id,
                "product_id": line.product_id,
                "sku": line.product.sku if line.product else None,
                "product_name": line.product.name if line.product else None,
                "variant_id": line.variant_id,
                "variant_name": line.variant.display_name if line.variant and hasattr(line.variant, "display_name") else None,
                "qty_ordered": float(line.qty_ordered),
                "qty_shipped": float(line.qty_shipped),
                "unit_price": float(line.unit_price),
                "discount_pct": line.discount_pct,
                "tax_rate": float(line.tax_rate),
                "line_total": float(line.line_total),
                "notes": line.notes,
            })

        return {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status.value if order.status else None,
            "subtotal": float(order.subtotal),
            "tax_amount": float(order.tax_amount),
            "discount_amount": float(order.discount_amount),
            "total": float(order.total),
            "currency": order.currency,
            "expected_date": order.expected_date.isoformat() if order.expected_date else None,
            "shipped_date": order.shipped_date.isoformat() if order.shipped_date else None,
            "delivered_date": order.delivered_date.isoformat() if order.delivered_date else None,
            "notes": order.notes,
            "lines": lines,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        }
