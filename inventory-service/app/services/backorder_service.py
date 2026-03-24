"""Backorder auto-split logic for Sales Orders.

When confirming a SO with insufficient stock for some lines, this service
splits the order: confirmable quantities stay on the original SO, and
pending quantities go to a new child (backorder) SO.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SalesOrder, SalesOrderLine, SalesOrderStatus
from app.repositories.product_repo import ProductRepository
from app.repositories.sales_order_repo import SalesOrderRepository
from app.repositories.stock_repo import StockRepository
from app.repositories.warehouse_repo import WarehouseRepository
from app.services.sales_order_service import recalculate_so_totals


class BackorderFullError(Exception):
    """Raised when ALL lines have 0 confirmable stock — no partial confirm."""
    pass


class BackorderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SalesOrderRepository(db)
        self.stock_repo = StockRepository(db)
        self.product_repo = ProductRepository(db)
        self.warehouse_repo = WarehouseRepository(db)

    async def analyze_and_split(
        self,
        order: SalesOrder,
        tenant_id: str,
        user_id: str | None = None,
    ) -> dict:
        """Analyze stock for each line and determine confirmable vs backordered quantities.

        Returns:
            {
                "needs_backorder": bool,
                "confirmable_lines": [(line, confirm_qty)],
                "backorder_lines": [(line, pending_qty)],
                "preview": [{ product_name, product_sku, warehouse_name, qty_ordered, qty_confirmable, qty_backordered }],
            }
        """
        confirmable: list[tuple[SalesOrderLine, Decimal]] = []
        backordered: list[tuple[SalesOrderLine, Decimal]] = []
        preview: list[dict] = []

        for line in order.lines:
            eff_wh = line.warehouse_id or order.warehouse_id
            qty = Decimal(str(line.qty_ordered))
            product = await self.product_repo.get_by_id(line.product_id, tenant_id)
            pname = product.name if product else line.product_id[:8]
            psku = product.sku if product else ""

            wh_name: str | None = None
            if eff_wh:
                wh = await self.warehouse_repo.get_by_id(eff_wh, tenant_id)
                wh_name = wh.name if wh else eff_wh[:8]

            if not eff_wh:
                # No warehouse: entire line goes to backorder
                confirmable.append((line, Decimal("0")))
                backordered.append((line, qty))
                preview.append({
                    "product_name": pname, "product_sku": psku, "warehouse_name": wh_name,
                    "qty_ordered": float(qty), "qty_confirmable": 0.0, "qty_backordered": float(qty),
                })
                continue

            level = await self.stock_repo.get_level(line.product_id, eff_wh, variant_id=line.variant_id)
            available = (level.qty_on_hand - level.qty_reserved) if level else Decimal("0")
            available = max(available, Decimal("0"))

            confirm_qty = min(qty, available)
            pending_qty = qty - confirm_qty

            confirmable.append((line, confirm_qty))
            if pending_qty > 0:
                backordered.append((line, pending_qty))

            preview.append({
                "product_name": pname, "product_sku": psku, "warehouse_name": wh_name,
                "qty_ordered": float(qty), "qty_confirmable": float(confirm_qty),
                "qty_backordered": float(pending_qty),
            })

        needs_backorder = len(backordered) > 0
        return {
            "needs_backorder": needs_backorder,
            "confirmable_lines": confirmable,
            "backorder_lines": backordered,
            "preview": preview,
        }

    async def create_backorder(
        self,
        parent_order: SalesOrder,
        backorder_lines: list[tuple[SalesOrderLine, Decimal]],
        confirmable_lines: list[tuple[SalesOrderLine, Decimal]],
        tenant_id: str,
        user_id: str | None = None,
    ) -> SalesOrder:
        """Create a child backorder SO with the pending lines/quantities.

        Also adjusts the parent order's quantities and totals.
        """
        # Count existing backorders to determine sequence number
        existing_count = len(parent_order.backorders) if parent_order.backorders else 0
        bo_number = existing_count + 1
        bo_order_number = f"{parent_order.order_number}-BO{bo_number}"

        # Create backorder SO — inherits global discount from parent
        bo_id = str(uuid.uuid4())
        backorder = SalesOrder(
            id=bo_id,
            tenant_id=tenant_id,
            order_number=bo_order_number,
            customer_id=parent_order.customer_id,
            status=SalesOrderStatus.draft,
            warehouse_id=parent_order.warehouse_id,
            shipping_address=parent_order.shipping_address,
            expected_date=parent_order.expected_date,
            currency=parent_order.currency,
            notes=f"Backorder automático de {parent_order.order_number}",
            is_backorder=True,
            parent_so_id=parent_order.id,
            backorder_number=bo_number,
            discount_pct=parent_order.discount_pct,
            discount_reason=parent_order.discount_reason,
            created_by=user_id,
            subtotal=Decimal("0"),
            tax_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            total=Decimal("0"),
        )
        self.db.add(backorder)
        await self.db.flush()

        # Create backorder lines
        bo_lines: list[SalesOrderLine] = []
        for orig_line, pending_qty in backorder_lines:
            bo_line = SalesOrderLine(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                order_id=bo_id,
                product_id=orig_line.product_id,
                variant_id=orig_line.variant_id,
                warehouse_id=orig_line.warehouse_id,
                qty_ordered=pending_qty,
                original_quantity=orig_line.qty_ordered,
                unit_price=orig_line.unit_price,
                discount_pct=orig_line.discount_pct,
                tax_rate=orig_line.tax_rate,
                notes=orig_line.notes,
                backorder_line_id=orig_line.id,
            )
            self.db.add(bo_line)
            bo_lines.append(bo_line)
        await self.db.flush()

        # Refresh to load the lines relationship (avoid lazy load in async)
        await self.db.refresh(backorder, ["lines"])
        recalculate_so_totals(backorder)

        # Adjust parent order lines quantities
        for orig_line, confirm_qty in confirmable_lines:
            orig_line.original_quantity = orig_line.qty_ordered
            orig_line.qty_ordered = confirm_qty

        recalculate_so_totals(parent_order)

        await self.db.flush()
        return await self.repo.get_by_id(bo_id, tenant_id)  # type: ignore[return-value]
