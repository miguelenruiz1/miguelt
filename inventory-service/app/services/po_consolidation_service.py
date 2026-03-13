"""Purchase Order consolidation logic."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.errors import ValidationError
from app.db.models.enums import POStatus
from app.db.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.db.models.supplier import Supplier
from app.repositories.po_repo import PORepository


class POConsolidationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PORepository(db)

    async def validate_consolidation(self, po_ids: list[str], tenant_id: str) -> list[PurchaseOrder]:
        if len(po_ids) < 2:
            raise ValidationError("Se necesitan al menos 2 órdenes de compra para consolidar")

        if len(set(po_ids)) != len(po_ids):
            raise ValidationError("Hay IDs duplicados en la lista")

        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id.in_(po_ids), PurchaseOrder.tenant_id == tenant_id)
            .options(
                joinedload(PurchaseOrder.lines).joinedload(PurchaseOrderLine.product),
                joinedload(PurchaseOrder.supplier),
            )
        )
        result = await self.db.execute(stmt)
        pos = list(result.scalars().unique().all())

        if len(pos) != len(po_ids):
            raise ValidationError("Una o más órdenes de compra no existen o no pertenecen al tenant")

        non_draft = [po for po in pos if po.status != POStatus.draft]
        if non_draft:
            numbers = ", ".join(po.po_number for po in non_draft)
            raise ValidationError(f"Solo se pueden consolidar OC en borrador. No están en borrador: {numbers}")

        supplier_ids = set(po.supplier_id for po in pos)
        if len(supplier_ids) > 1:
            raise ValidationError("Todas las órdenes de compra deben ser del mismo proveedor")

        return pos

    async def consolidate(self, po_ids: list[str], tenant_id: str, user_id: str) -> dict:
        pos = await self.validate_consolidation(po_ids, tenant_id)
        supplier_id = pos[0].supplier_id

        # Generate consolidated PO number
        po_number = await self.repo.next_po_number(tenant_id)

        # Combine lines: group by (product_id, variant_id, warehouse from PO header or location_id)
        lines_map: dict[tuple, dict] = {}
        total_original_lines = 0
        for po in pos:
            wh_id = po.warehouse_id or ""
            for line in po.lines:
                total_original_lines += 1
                key = (line.product_id, line.variant_id or "", line.location_id or "", wh_id)
                if key in lines_map:
                    existing = lines_map[key]
                    old_qty = existing["qty_ordered"]
                    add_qty = line.qty_ordered
                    # Weighted average unit cost
                    total_cost = (existing["unit_cost"] * old_qty) + (line.unit_cost * add_qty)
                    new_qty = old_qty + add_qty
                    existing["qty_ordered"] = new_qty
                    existing["unit_cost"] = (total_cost / new_qty).quantize(Decimal("0.0001"))
                    existing["line_total"] = (new_qty * existing["unit_cost"]).quantize(Decimal("0.0001"))
                    existing["source_pos"].append(po.po_number)
                else:
                    lines_map[key] = {
                        "product_id": line.product_id,
                        "variant_id": line.variant_id,
                        "location_id": line.location_id,
                        "qty_ordered": line.qty_ordered,
                        "unit_cost": line.unit_cost,
                        "line_total": line.line_total,
                        "notes": line.notes,
                        "source_pos": [po.po_number],
                    }

        lines_merged = total_original_lines - len(lines_map)

        # Use earliest expected_date
        expected_dates = [po.expected_date for po in pos if po.expected_date]
        expected_date = min(expected_dates) if expected_dates else None

        # Use warehouse from first PO if all share the same, else None
        wh_ids = set(po.warehouse_id for po in pos if po.warehouse_id)
        warehouse_id = wh_ids.pop() if len(wh_ids) == 1 else None

        # Create consolidated PO
        consolidated = PurchaseOrder(
            id=str(uuid4()),
            tenant_id=tenant_id,
            po_number=po_number,
            supplier_id=supplier_id,
            status=POStatus.draft,
            warehouse_id=warehouse_id,
            expected_date=expected_date,
            is_consolidated=True,
            consolidated_from_ids=[str(po.id) for po in pos],
            consolidated_at=datetime.now(timezone.utc),
            consolidated_by=user_id,
            is_auto_generated=False,
            notes=f"Consolidación de: {', '.join(po.po_number for po in pos)}",
            created_by=user_id,
        )
        self.db.add(consolidated)
        await self.db.flush()

        # Create consolidated lines
        for line_data in lines_map.values():
            source_note = (
                f"Consolidado desde: {', '.join(line_data['source_pos'])}"
                if len(line_data["source_pos"]) > 1
                else None
            )
            notes = source_note or line_data.get("notes")
            new_line = PurchaseOrderLine(
                id=str(uuid4()),
                tenant_id=tenant_id,
                po_id=consolidated.id,
                product_id=line_data["product_id"],
                variant_id=line_data["variant_id"],
                qty_ordered=line_data["qty_ordered"],
                qty_received=Decimal("0"),
                unit_cost=line_data["unit_cost"],
                line_total=line_data["line_total"],
                location_id=line_data["location_id"],
                notes=notes,
            )
            self.db.add(new_line)

        # Mark originals as consolidated
        for po in pos:
            po.status = POStatus.consolidated
            po.parent_consolidated_id = consolidated.id

        await self.db.flush()

        # Re-fetch the consolidated PO with relationships
        consolidated = await self.repo.get_by_id(consolidated.id, tenant_id)

        msg = f"{len(pos)} OC consolidadas en {po_number}."
        if lines_merged > 0:
            msg += f" {lines_merged} líneas del mismo producto fueron combinadas."

        return {
            "consolidated_po": consolidated,
            "original_pos": pos,
            "lines_merged": lines_merged,
            "message": msg,
        }

    async def deconsolidate(self, consolidated_po_id: str, tenant_id: str) -> list[PurchaseOrder]:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == consolidated_po_id, PurchaseOrder.tenant_id == tenant_id)
            .options(joinedload(PurchaseOrder.lines))
        )
        result = await self.db.execute(stmt)
        consolidated = result.scalar_one_or_none()

        if not consolidated:
            raise ValidationError("Orden de compra no encontrada")
        if not consolidated.is_consolidated:
            raise ValidationError("Esta orden de compra no es una consolidación")
        if consolidated.status != POStatus.draft:
            raise ValidationError("Solo se puede revertir una consolidación si está en borrador")

        original_ids = consolidated.consolidated_from_ids or []
        if not original_ids:
            raise ValidationError("No se encontraron las órdenes originales")

        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id.in_(original_ids), PurchaseOrder.tenant_id == tenant_id)
            .options(joinedload(PurchaseOrder.lines))
        )
        result = await self.db.execute(stmt)
        originals = list(result.scalars().unique().all())

        for po in originals:
            po.status = POStatus.draft
            po.parent_consolidated_id = None

        consolidated.status = POStatus.canceled

        await self.db.flush()
        return originals

    async def get_consolidation_candidates(self, tenant_id: str) -> list[dict]:
        """Find suppliers with 2+ draft POs."""
        stmt = (
            select(
                PurchaseOrder.supplier_id,
                func.count(PurchaseOrder.id).label("po_count"),
            )
            .where(
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.status == POStatus.draft,
            )
            .group_by(PurchaseOrder.supplier_id)
            .having(func.count(PurchaseOrder.id) >= 2)
        )
        result = await self.db.execute(stmt)
        groups = result.all()

        candidates = []
        for supplier_id, po_count in groups:
            sup_result = await self.db.execute(
                select(Supplier).where(Supplier.id == supplier_id)
            )
            supplier = sup_result.scalar_one_or_none()

            pos_stmt = (
                select(PurchaseOrder)
                .where(
                    PurchaseOrder.tenant_id == tenant_id,
                    PurchaseOrder.supplier_id == supplier_id,
                    PurchaseOrder.status == POStatus.draft,
                )
                .options(
                    joinedload(PurchaseOrder.lines),
                    joinedload(PurchaseOrder.supplier),
                )
                .order_by(PurchaseOrder.created_at.desc())
            )
            pos_result = await self.db.execute(pos_stmt)
            pos = list(pos_result.scalars().unique().all())

            total_amount = sum(
                float(line.line_total or 0) for po in pos for line in po.lines
            )

            candidates.append({
                "supplier_id": supplier_id,
                "supplier_name": supplier.name if supplier else "Desconocido",
                "po_count": len(pos),
                "total_amount": total_amount,
                "pos": pos,
            })

        return candidates

    async def get_consolidation_info(self, po_id: str, tenant_id: str) -> dict:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id, PurchaseOrder.tenant_id == tenant_id)
            .options(joinedload(PurchaseOrder.lines))
        )
        result = await self.db.execute(stmt)
        po = result.scalar_one_or_none()

        if not po:
            raise ValidationError("Orden de compra no encontrada")

        if po.is_consolidated:
            original_ids = po.consolidated_from_ids or []
            originals_stmt = (
                select(PurchaseOrder)
                .where(PurchaseOrder.id.in_(original_ids), PurchaseOrder.tenant_id == tenant_id)
                .options(joinedload(PurchaseOrder.lines), joinedload(PurchaseOrder.supplier))
            )
            originals_result = await self.db.execute(originals_stmt)
            originals = list(originals_result.scalars().unique().all())
            return {
                "type": "consolidated",
                "consolidated_po": po,
                "original_pos": originals,
                "consolidated_at": po.consolidated_at,
                "consolidated_by": po.consolidated_by,
            }
        elif po.parent_consolidated_id:
            parent_stmt = (
                select(PurchaseOrder)
                .where(PurchaseOrder.id == po.parent_consolidated_id, PurchaseOrder.tenant_id == tenant_id)
                .options(joinedload(PurchaseOrder.lines), joinedload(PurchaseOrder.supplier))
            )
            parent_result = await self.db.execute(parent_stmt)
            parent = parent_result.scalar_one_or_none()
            return {
                "type": "original",
                "consolidated_po": parent,
                "original_pos": None,
                "consolidated_at": parent.consolidated_at if parent else None,
                "consolidated_by": parent.consolidated_by if parent else None,
            }
        else:
            return {
                "type": "none",
                "consolidated_po": None,
                "original_pos": None,
                "consolidated_at": None,
                "consolidated_by": None,
            }
