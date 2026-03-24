"""Automatic reorder service — creates draft POs when stock falls below ROP."""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import POStatus, Product, PurchaseOrder, StockLevel
from app.repositories.po_repo import PORepository
from app.repositories.stock_repo import StockRepository

log = logging.getLogger("inventory.reorder")


class ReorderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.po_repo = PORepository(db)
        self.stock_repo = StockRepository(db)

    async def check_and_trigger_reorder(
        self,
        product_id: str,
        tenant_id: str,
        warehouse_id: str | None = None,
    ) -> PurchaseOrder | None:
        """Check if a single product needs reorder and create a draft PO if so.

        Returns the created PO or None if no reorder is needed.
        """
        product = await self._load_product(product_id, tenant_id)
        if not product:
            return None
        if not product.auto_reorder:
            return None
        if not product.preferred_supplier_id:
            return None
        if product.reorder_point <= 0:
            return None

        # Get aggregated available stock across all warehouses (or specific one)
        available = await self._get_available_stock(product_id, tenant_id, warehouse_id)
        if available >= product.reorder_point:
            return None

        # Check for existing open auto-PO for this product to avoid duplicates
        has_open = await self._has_open_auto_po(product_id, tenant_id)
        if has_open:
            log.debug("skip_reorder product=%s reason=open_po_exists", product_id)
            return None

        # Determine reorder warehouse (use first warehouse with stock or the specific one)
        target_wh = warehouse_id
        if not target_wh:
            target_wh = await self._pick_warehouse(product_id, tenant_id)

        # Create draft PO
        po = await self._create_reorder_po(product, tenant_id, available, target_wh)
        log.info(
            "auto_reorder_created po=%s product=%s available=%s rop=%s qty=%s",
            po.po_number, product.sku, available, product.reorder_point, product.reorder_quantity,
        )
        return po

    async def check_all_products_reorder(self, tenant_id: str) -> list[PurchaseOrder]:
        """Scan all products with auto_reorder=True and create POs as needed.

        Used by the daily scheduler.
        """
        result = await self.db.execute(
            select(Product)
            .options(joinedload(Product.preferred_supplier))
            .where(
                Product.tenant_id == tenant_id,
                Product.is_active == True,  # noqa: E712
                Product.auto_reorder == True,  # noqa: E712
                Product.preferred_supplier_id.isnot(None),
                Product.reorder_point > 0,
            )
        )
        products = list(result.scalars().unique().all())
        created_pos: list[PurchaseOrder] = []

        for product in products:
            try:
                po = await self.check_and_trigger_reorder(product.id, tenant_id)
                if po:
                    created_pos.append(po)
            except Exception:
                log.exception("reorder_check_failed product=%s", product.id)

        return created_pos

    async def get_reorder_config(self, tenant_id: str) -> list[dict]:
        """Return reorder configuration for all products with auto_reorder enabled."""
        result = await self.db.execute(
            select(Product)
            .options(joinedload(Product.preferred_supplier))
            .where(
                Product.tenant_id == tenant_id,
                Product.is_active == True,  # noqa: E712
                Product.auto_reorder == True,  # noqa: E712
            )
            .order_by(Product.name)
        )
        products = list(result.scalars().unique().all())

        configs = []
        for p in products:
            available = await self._get_available_stock(p.id, tenant_id)
            has_open_po = await self._has_open_auto_po(p.id, tenant_id)
            configs.append({
                "product_id": p.id,
                "product_name": p.name,
                "product_sku": p.sku,
                "reorder_point": p.reorder_point,
                "reorder_quantity": p.reorder_quantity,
                "preferred_supplier_id": p.preferred_supplier_id,
                "preferred_supplier_name": p.preferred_supplier.name if p.preferred_supplier else None,
                "current_stock": float(available),
                "below_rop": available < p.reorder_point,
                "has_open_po": has_open_po,
            })
        return configs

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _load_product(self, product_id: str, tenant_id: str) -> Product | None:
        result = await self.db.execute(
            select(Product)
            .options(joinedload(Product.preferred_supplier))
            .where(Product.id == product_id, Product.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def _get_available_stock(
        self, product_id: str, tenant_id: str, warehouse_id: str | None = None,
    ) -> Decimal:
        """Sum of (qty_on_hand - qty_reserved) across warehouses."""
        q = select(StockLevel).where(
            StockLevel.product_id == product_id,
            StockLevel.tenant_id == tenant_id,
        )
        if warehouse_id:
            q = q.where(StockLevel.warehouse_id == warehouse_id)
        result = await self.db.execute(q)
        levels = result.scalars().all()
        return sum((sl.qty_on_hand - sl.qty_reserved) for sl in levels) if levels else Decimal("0")

    async def _has_open_auto_po(self, product_id: str, tenant_id: str) -> bool:
        """Check if there's already an open (draft/sent/confirmed/partial) auto PO containing this product."""
        from app.db.models import PurchaseOrderLine
        result = await self.db.execute(
            select(PurchaseOrder.id)
            .join(PurchaseOrderLine, PurchaseOrderLine.po_id == PurchaseOrder.id)
            .where(
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.is_auto_generated == True,  # noqa: E712
                PurchaseOrder.status.in_([
                    POStatus.draft, POStatus.sent, POStatus.confirmed, POStatus.partial,
                ]),
                PurchaseOrderLine.product_id == product_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _pick_warehouse(self, product_id: str, tenant_id: str) -> str | None:
        """Pick the warehouse with the most stock for this product (for PO destination)."""
        result = await self.db.execute(
            select(StockLevel.warehouse_id)
            .where(
                StockLevel.product_id == product_id,
                StockLevel.tenant_id == tenant_id,
            )
            .order_by(StockLevel.qty_on_hand.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            return row
        # Fallback: first warehouse in tenant
        from app.db.models import Warehouse
        result2 = await self.db.execute(
            select(Warehouse.id)
            .where(Warehouse.tenant_id == tenant_id)
            .limit(1)
        )
        return result2.scalar_one_or_none()

    async def _create_reorder_po(
        self,
        product: Product,
        tenant_id: str,
        current_stock: Decimal,
        warehouse_id: str | None,
    ) -> PurchaseOrder:
        """Create a draft PO for the product's preferred supplier."""
        po_number = await self.po_repo.next_po_number(tenant_id)
        po_data = {
            "tenant_id": tenant_id,
            "po_number": po_number,
            "supplier_id": product.preferred_supplier_id,
            "status": POStatus.draft,
            "warehouse_id": warehouse_id,
            "is_auto_generated": True,
            "reorder_trigger_stock": current_stock,
            "notes": f"Auto-reorden: {product.name} ({product.sku}) stock={current_stock} < ROP={product.reorder_point}",
            "created_by": "system:auto-reorder",
            "lines": [
                {
                    "product_id": product.id,
                    "qty_ordered": Decimal(str(product.reorder_quantity)),
                    "unit_cost": product.last_purchase_cost or Decimal("0"),
                    "line_total": (product.last_purchase_cost or Decimal("0")) * Decimal(str(product.reorder_quantity)),
                },
            ],
        }
        return await self.po_repo.create(po_data)
