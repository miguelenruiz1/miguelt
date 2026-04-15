"""GRN service — formal Goods Receipt Note creation that also posts the PO receipt."""
from __future__ import annotations

from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models import PurchaseOrder, PurchaseOrderLine
from app.db.models.goods_receipt import GoodsReceipt
from app.repositories.grn_repo import GRNRepository
from app.services.po_service import POService


class GRNService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GRNRepository(db)

    async def create_grn(
        self,
        *,
        tenant_id: str,
        po_id: str,
        receipt_date,
        notes: str | None,
        attachments: list | None,
        lines: list[dict],
        performed_by: str | None,
    ) -> GoodsReceipt:
        # Validate PO exists
        po_q = await self.db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.id == po_id,
                PurchaseOrder.tenant_id == tenant_id,
            )
        )
        po = po_q.scalar_one_or_none()
        if not po:
            raise NotFoundError(f"PO {po_id!r} not found")

        # Load PO lines to validate + compute expected qty + discrepancy
        po_line_ids = [ln["po_line_id"] for ln in lines]
        pol_q = await self.db.execute(
            select(PurchaseOrderLine).where(PurchaseOrderLine.id.in_(po_line_ids))
        )
        po_line_map = {pol.id: pol for pol in pol_q.scalars().all()}

        grn_lines: list[dict] = []
        has_discrepancy = False

        for ln in lines:
            pol = po_line_map.get(ln["po_line_id"])
            if not pol or pol.po_id != po_id:
                raise ValidationError(f"PO line {ln['po_line_id']!r} does not belong to PO {po_id!r}")

            qty_received = Decimal(str(ln["qty_received"]))
            qty_expected = pol.qty_ordered - pol.qty_received  # remaining expected
            qty_discrepancy = qty_received - qty_expected
            if qty_discrepancy != 0:
                has_discrepancy = True

            grn_lines.append({
                "po_line_id": pol.id,
                "product_id": pol.product_id,
                "qty_expected": qty_expected,
                "qty_received": qty_received,
                "qty_discrepancy": qty_discrepancy,
                "batch_number": ln.get("batch_number"),
                "discrepancy_reason": ln.get("discrepancy_reason"),
                "notes": ln.get("notes"),
            })

        # Post the receipt through PO service (updates qty_received, stock, batches, status)
        po_svc = POService(self.db)
        receive_payload = [
            {
                "line_id": ln["po_line_id"],
                "qty_received": Decimal(str(ln["qty_received"])),
                "uom": "primary",
                "batch_number": ln.get("batch_number"),
            }
            for ln in lines
        ]
        await po_svc.receive_items(
            po_id=po_id,
            tenant_id=tenant_id,
            line_receipts=receive_payload,
            performed_by=performed_by,
        )

        # Generate GRN number + persist
        grn_number = await self.repo.next_grn_number(tenant_id)
        grn = await self.repo.create(
            tenant_id=tenant_id,
            purchase_order_id=po_id,
            grn_number=grn_number,
            receipt_date=receipt_date,
            received_by=performed_by,
            notes=notes,
            attachments=attachments,
            has_discrepancy=has_discrepancy,
            lines=grn_lines,
        )
        return grn

    async def get_grn(self, tenant_id: str, grn_id: str) -> GoodsReceipt:
        grn = await self.repo.get(tenant_id, grn_id)
        if not grn:
            raise NotFoundError(f"GRN {grn_id!r} not found")
        return grn

    async def list_for_po(self, tenant_id: str, po_id: str) -> list[GoodsReceipt]:
        return await self.repo.list_by_po(tenant_id, po_id)
