"""Business logic for Purchase Orders."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models import POStatus, Product, PurchaseOrder, Supplier
from app.db.models.cost_history import ProductCostHistory
from app.db.models.partner import BusinessPartner
from app.repositories.batch_repo import BatchRepository
from app.repositories.po_repo import PORepository
from app.repositories.product_repo import ProductRepository
from app.repositories.supplier_repo import SupplierRepository
from app.repositories.warehouse_repo import WarehouseRepository
from app.services.pricing_engine import PricingEngine
from app.services.stock_service import StockService


class POService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PORepository(db)
        self.supplier_repo = SupplierRepository(db)
        self.warehouse_repo = WarehouseRepository(db)
        self.stock_service = StockService(db)

    async def _find_supplier(self, supplier_id: str, tenant_id: str):
        """Find supplier in suppliers table or partners table."""
        supplier = await self.supplier_repo.get_by_id(supplier_id, tenant_id)
        if supplier:
            return supplier
        # Fallback: check partners table
        result = await self.db.execute(
            select(BusinessPartner).where(
                BusinessPartner.id == supplier_id,
                BusinessPartner.tenant_id == tenant_id,
                BusinessPartner.is_supplier.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def resolve_supplier_name(self, supplier_id: str | None, tenant_id: str) -> str | None:
        if not supplier_id:
            return None
        supplier = await self._find_supplier(supplier_id, tenant_id)
        return supplier.name if supplier else None

    async def list(
        self,
        tenant_id: str,
        status: POStatus | None = None,
        supplier_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[PurchaseOrder], int]:
        return await self.repo.list(
            tenant_id=tenant_id,
            status=status,
            supplier_id=supplier_id,
            offset=offset,
            limit=limit,
        )

    async def get(self, po_id: str, tenant_id: str) -> PurchaseOrder:
        po = await self.repo.get_by_id(po_id, tenant_id)
        if not po:
            raise NotFoundError(f"Purchase order {po_id!r} not found")
        return po

    async def _ensure_legacy_supplier(self, partner: BusinessPartner, tenant_id: str):
        """If supplier comes from business_partners, ensure a legacy supplier record exists for FK."""
        existing = await self.supplier_repo.get_by_id(partner.id, tenant_id)
        if not existing:
            legacy = Supplier(
                id=partner.id,
                tenant_id=tenant_id,
                name=partner.name,
                code=partner.code or partner.id[:8],
                contact_name=partner.contact_name,
                email=partner.email,
                phone=partner.phone,
                is_active=True,
            )
            self.db.add(legacy)
            await self.db.flush()

    async def create_draft(self, tenant_id: str, data: dict) -> PurchaseOrder:
        supplier = await self._find_supplier(data["supplier_id"], tenant_id)
        if not supplier:
            raise NotFoundError(f"Proveedor {data['supplier_id']!r} no encontrado")

        # Ensure legacy supplier record exists for FK constraint
        if isinstance(supplier, BusinessPartner):
            await self._ensure_legacy_supplier(supplier, tenant_id)

        lines = data.get("lines", [])
        if not lines:
            raise ValidationError("La orden de compra debe tener al menos una línea")

        # Validate cost on every line
        for i, line in enumerate(lines):
            cost = line.get("unit_cost")
            if cost is None or Decimal(str(cost)) <= 0:
                raise ValidationError(f"Línea {i+1}: el costo unitario es obligatorio y debe ser mayor a cero")
            qty = line.get("qty_ordered")
            if qty is None or Decimal(str(qty)) <= 0:
                raise ValidationError(f"Línea {i+1}: la cantidad es obligatoria y debe ser mayor a cero")

        po_number = await self.repo.next_po_number(tenant_id)
        # Resolve warehouse_id: explicit → tenant default → null
        if not data.get("warehouse_id"):
            default_wh = await self.warehouse_repo.get_default(tenant_id)
            if default_wh is not None:
                data = {**data, "warehouse_id": default_wh.id}
        return await self.repo.create({
            "tenant_id": tenant_id,
            "po_number": po_number,
            "status": POStatus.draft,
            **data,
        })

    async def delete(self, po_id: str, tenant_id: str) -> None:
        po = await self.get(po_id, tenant_id)
        if po.status != POStatus.draft:
            raise ValidationError(
                f"Solo se pueden eliminar POs en estado 'draft', actual: '{po.status.value}'"
            )
        await self.repo.delete(po)

    async def update(self, po_id: str, tenant_id: str, data: dict) -> PurchaseOrder:
        po = await self.get(po_id, tenant_id)
        if po.status in (POStatus.received, POStatus.canceled, POStatus.consolidated):
            raise ValidationError(f"Cannot edit a PO with status {po.status}")
        return await self.repo.update(po, data)

    async def send(self, po_id: str, tenant_id: str, user_id: str | None = None) -> PurchaseOrder:
        """Send PO to supplier. Status must be draft or approved."""
        po = await self.get(po_id, tenant_id)
        if po.status not in (POStatus.draft, POStatus.approved):
            raise ValidationError(
                f"Solo se pueden enviar OCs en borrador o aprobadas, actual: '{po.status.value}'"
            )
        if not po.lines:
            raise ValidationError("La OC debe tener al menos una línea para enviar")

        update_data = {
            "status": POStatus.sent,
            "sent_at": datetime.now(timezone.utc),
            "sent_by": user_id,
        }
        return await self.repo.update(po, update_data)

    async def confirm(self, po_id: str, tenant_id: str, user_id: str | None = None, expected_date=None) -> PurchaseOrder:
        """Confirm PO (supplier accepted). Status must be sent."""
        po = await self.get(po_id, tenant_id)
        if po.status != POStatus.sent:
            raise ValidationError("Solo se pueden confirmar OCs enviadas")

        update_data = {
            "status": POStatus.confirmed,
            "confirmed_at": datetime.now(timezone.utc),
            "confirmed_by": user_id,
        }
        if expected_date:
            update_data["expected_date"] = expected_date
        return await self.repo.update(po, update_data)

    async def cancel(self, po_id: str, tenant_id: str) -> PurchaseOrder:
        po = await self.get(po_id, tenant_id)
        terminal = (POStatus.received, POStatus.canceled, POStatus.consolidated)
        if po.status in terminal:
            raise ValidationError(f"No se puede cancelar una OC con estado '{po.status.value}'")
        return await self.repo.update(po, {"status": POStatus.canceled})

    async def receive_items(
        self,
        po_id: str,
        tenant_id: str,
        line_receipts: list[dict],
        performed_by: str | None = None,
    ) -> PurchaseOrder:
        """Receive quantities per line, create stock movements, cost history, and recalculate prices.

        Takes a SELECT FOR UPDATE on the PO so two concurrent receives can't
        both pass the status check and cause double-receipts on the same lines.
        """
        # Lock the PO row to serialize concurrent receive_items calls
        from sqlalchemy import select as _select
        locked = await self.db.execute(
            _select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id, PurchaseOrder.tenant_id == tenant_id)
            .with_for_update()
        )
        if locked.scalar_one_or_none() is None:
            raise NotFoundError(f"PO {po_id!r} not found")

        po = await self.get(po_id, tenant_id)
        if po.status in (POStatus.received, POStatus.canceled, POStatus.consolidated):
            raise ValidationError(f"No se puede recibir una OC con estado '{po.status.value}'")
        if not po.warehouse_id:
            raise ValidationError("PO has no destination warehouse set")

        product_repo = ProductRepository(self.db)
        pricing = PricingEngine(self.db)

        # Resolve supplier name once
        supplier = await self._find_supplier(po.supplier_id, tenant_id)
        supplier_name = supplier.name if supplier else "Desconocido"

        # ── Bulk pre-fetch to avoid N+1 in receive loops ──
        # Fetch all PO lines referenced in receipts in a single query.
        line_ids = [r["line_id"] for r in line_receipts]
        from app.db.models import PurchaseOrderLine
        from sqlalchemy import select as _select
        lines_q = await self.db.execute(
            _select(PurchaseOrderLine).where(PurchaseOrderLine.id.in_(line_ids))
        )
        line_map: dict[str, PurchaseOrderLine] = {l.id: l for l in lines_q.scalars().all()}

        # Fetch all products referenced in those lines in one query.
        product_ids = list({l.product_id for l in line_map.values()})
        if product_ids:
            prods_q = await self.db.execute(
                _select(Product).where(
                    Product.id.in_(product_ids),
                    Product.tenant_id == tenant_id,
                )
            )
            product_map: dict[str, Product] = {p.id: p for p in prods_q.scalars().all()}
        else:
            product_map = {}

        for receipt in line_receipts:
            line = line_map.get(receipt["line_id"])
            if not line or line.po_id != po_id:
                raise NotFoundError(f"PO line {receipt['line_id']!r} not found")

            qty = Decimal(str(receipt["qty_received"]))
            if qty <= 0:
                continue

            if not line.unit_cost or line.unit_cost <= 0:
                raise ValidationError(
                    f"La línea {line.product_id[:8]} no tiene costo unitario. "
                    "Edite la OC y asigne un costo antes de recibir."
                )

            new_received = line.qty_received + qty
            if new_received > line.qty_ordered:
                raise ValidationError(
                    f"Cannot receive more than ordered on line {line.id}: "
                    f"ordered={line.qty_ordered}, already received={line.qty_received}, new={qty}"
                )

            await self.repo.update_line(line, {"qty_received": new_received})

            # ── Auto-create or find batch if batch_number provided ────
            batch_id = None
            batch_number = receipt.get("batch_number")
            if batch_number:
                batch_repo = BatchRepository(self.db)
                existing = await batch_repo.find_by_number(
                    tenant_id, line.product_id, batch_number
                )
                if existing:
                    batch_id = existing.id
                    # Atomic increment to avoid lost updates under concurrency
                    await batch_repo.increment_quantity(existing.id, qty)
                else:
                    batch = await batch_repo.create(tenant_id, {
                        "entity_id": line.product_id,
                        "batch_number": batch_number,
                        "quantity": qty,
                        "cost": line.unit_cost,
                        "manufacture_date": receipt.get("manufacture_date"),
                        "expiration_date": receipt.get("expiration_date"),
                        "notes": f"Auto-creado al recibir OC {po.po_number}",
                        "created_by": performed_by or "system",
                    })
                    batch_id = batch.id

            # Receive stock (creates movement + updates qty_on_hand)
            await self.stock_service.receive(
                tenant_id=tenant_id,
                product_id=line.product_id,
                warehouse_id=po.warehouse_id,
                quantity=qty,
                unit_cost=line.unit_cost,
                reference=po.po_number,
                performed_by=performed_by,
                variant_id=line.variant_id,
                location_id=line.location_id,
                uom=receipt.get("uom", "primary"),
                batch_id=batch_id,
                batch_number=batch_number,
            )

            # ── Cost history & dynamic pricing ────────────────────────
            # For now, qty_in_base_uom = qty (primary UoM assumed)
            # UoM conversion will be enhanced when UoMs are initialized
            qty_base = qty
            cost_per_base = line.unit_cost

            # Create cost history record
            cost_record = ProductCostHistory(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                product_id=line.product_id,
                variant_id=line.variant_id,
                purchase_order_id=po.id,
                purchase_order_line_id=line.id,
                supplier_id=po.supplier_id,
                supplier_name=supplier_name,
                uom_purchased=receipt.get("uom", "primary"),
                qty_purchased=qty,
                qty_in_base_uom=qty_base,
                unit_cost_purchased=line.unit_cost,
                unit_cost_base_uom=cost_per_base,
                total_cost=qty * line.unit_cost,
                received_at=datetime.now(timezone.utc),
            )
            self.db.add(cost_record)

            # Update product denormalized pricing fields (from pre-fetched map)
            product = product_map.get(line.product_id)
            if product:
                product.last_purchase_cost = cost_per_base
                product.last_purchase_date = datetime.now(timezone.utc)
                product.last_purchase_supplier = supplier_name
                await self.db.flush()  # Persist cost before recalculating prices

                # Recalculate suggested & minimum sale prices
                await pricing.recalculate_product_prices(product, tenant_id)

                # ── Margin danger check ──────────────────────────────────
                if product.margin_minimum is not None and product.suggested_sale_price:
                    new_cost = cost_per_base
                    sale_price = product.suggested_sale_price
                    if sale_price > 0:
                        actual_margin = ((sale_price - new_cost) / sale_price) * 100
                        if actual_margin < float(product.margin_minimum):
                            # Fire-and-forget notification
                            try:
                                from app.services.po_notification_service import PONotificationService
                                notif = PONotificationService(self.db)
                                await notif.notify_margin_danger(
                                    tenant_id=tenant_id,
                                    product_name=product.name,
                                    product_sku=product.sku,
                                    new_cost=float(new_cost),
                                    actual_margin=round(float(actual_margin), 1),
                                    minimum_margin=float(product.margin_minimum),
                                    po_number=po.po_number,
                                )
                            except Exception:
                                pass  # Best-effort notification

        await self.db.flush()

        # Reload PO with lines
        po = await self.get(po_id, tenant_id)
        all_received = all(line.qty_received >= line.qty_ordered for line in po.lines)
        any_received = any(line.qty_received > 0 for line in po.lines)

        from datetime import date
        new_status = POStatus.received if all_received else (POStatus.partial if any_received else po.status)
        received_date = date.today() if all_received else po.received_date

        return await self.repo.update(po, {"status": new_status, "received_date": received_date})
