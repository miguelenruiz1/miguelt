"""Business logic for Purchase Orders."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models import POStatus, PurchaseOrder
from app.repositories.po_repo import PORepository
from app.repositories.supplier_repo import SupplierRepository
from app.services.stock_service import StockService


class POService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PORepository(db)
        self.supplier_repo = SupplierRepository(db)
        self.stock_service = StockService(db)

    async def resolve_supplier_name(self, supplier_id: str | None, tenant_id: str) -> str | None:
        if not supplier_id:
            return None
        supplier = await self.supplier_repo.get_by_id(supplier_id, tenant_id)
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

    async def create_draft(self, tenant_id: str, data: dict) -> PurchaseOrder:
        supplier = await self.supplier_repo.get_by_id(data["supplier_id"], tenant_id)
        if not supplier:
            raise NotFoundError(f"Supplier {data['supplier_id']!r} not found")

        po_number = await self.repo.next_po_number(tenant_id)
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

    async def send(self, po_id: str, tenant_id: str) -> PurchaseOrder:
        po = await self.get(po_id, tenant_id)
        if po.status != POStatus.draft:
            raise ValidationError("Only draft POs can be sent")
        return await self.repo.update(po, {"status": POStatus.sent})

    async def confirm(self, po_id: str, tenant_id: str) -> PurchaseOrder:
        po = await self.get(po_id, tenant_id)
        if po.status not in (POStatus.draft, POStatus.sent):
            raise ValidationError("PO must be draft or sent to confirm")
        return await self.repo.update(po, {"status": POStatus.confirmed})

    async def cancel(self, po_id: str, tenant_id: str) -> PurchaseOrder:
        po = await self.get(po_id, tenant_id)
        if po.status in (POStatus.received, POStatus.canceled, POStatus.consolidated):
            raise ValidationError(f"Cannot cancel a PO with status {po.status}")
        return await self.repo.update(po, {"status": POStatus.canceled})

    async def receive_items(
        self,
        po_id: str,
        tenant_id: str,
        line_receipts: list[dict],
        performed_by: str | None = None,
    ) -> PurchaseOrder:
        """Receive quantities per line and create stock movements."""
        po = await self.get(po_id, tenant_id)
        if po.status not in (POStatus.confirmed, POStatus.partial):
            raise ValidationError("PO must be confirmed or partial to receive items")
        if not po.warehouse_id:
            raise ValidationError("PO has no destination warehouse set")

        total_ordered = Decimal("0")
        total_received = Decimal("0")

        for receipt in line_receipts:
            line = await self.repo.get_line(receipt["line_id"], po_id)
            if not line:
                raise NotFoundError(f"PO line {receipt['line_id']!r} not found")

            qty = Decimal(str(receipt["qty_received"]))
            if qty <= 0:
                continue

            new_received = line.qty_received + qty
            if new_received > line.qty_ordered:
                raise ValidationError(
                    f"Cannot receive more than ordered on line {line.id}: "
                    f"ordered={line.qty_ordered}, already received={line.qty_received}, new={qty}"
                )

            await self.repo.update_line(line, {"qty_received": new_received})

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
            )

        # Reload PO with lines
        po = await self.get(po_id, tenant_id)
        all_received = all(line.qty_received >= line.qty_ordered for line in po.lines)
        any_received = any(line.qty_received > 0 for line in po.lines)

        from datetime import date
        new_status = POStatus.received if all_received else (POStatus.partial if any_received else po.status)
        received_date = date.today() if all_received else po.received_date

        return await self.repo.update(po, {"status": new_status, "received_date": received_date})
