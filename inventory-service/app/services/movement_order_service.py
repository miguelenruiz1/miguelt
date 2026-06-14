"""WM movement-order service (internal bin->bin documents).

Implements the SAP-WM rule "no physical movement without a document": a movement
order has source/dest bins per line and two confirmations (pick + putaway). On
full confirmation it posts a kardex ``StockMovement`` and relocates the quant.

NOTE: this is INTERNAL warehouse movement. Freight/transport between locations
or to customers is the logistics module (trace-service) — not here.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models import (
    OperationType, StockLevel, StockMovement, TransferOrder, TransferOrderLine,
    WarehouseLocation,
)
from app.domain.schemas.wm_transfer import ConfirmLineIn, MovementOrderCreate
from app.repositories.sequence_repo import SequenceRepository

# Default operation types (SAP-style movement classes) seeded per tenant.
DEFAULT_OPERATION_TYPES = [
    {"code": "101", "name": "Recepción de compra", "direction": "inbound",
     "movement_type": "purchase", "source_zone": "GR-ZONE", "dest_zone": "STOCK"},
    {"code": "201", "name": "Salida por venta", "direction": "outbound",
     "movement_type": "sale", "source_zone": "STOCK", "dest_zone": "GI-ZONE"},
    {"code": "311", "name": "Traslado interno", "direction": "internal",
     "movement_type": "transfer", "source_zone": "STOCK", "dest_zone": "STOCK"},
    {"code": "501", "name": "Ingreso de producción", "direction": "inbound",
     "movement_type": "production_in", "source_zone": "PROD-ZONE", "dest_zone": "STOCK"},
    {"code": "601", "name": "Consumo a producción", "direction": "outbound",
     "movement_type": "production_out", "source_zone": "STOCK", "dest_zone": "PROD-ZONE"},
]

# Interim (logical) zones auto-created per warehouse (SAP 9xx).
INTERIM_ZONES = [
    ("GR-ZONE", "Zona de recepción"),
    ("GI-ZONE", "Zona de despacho"),
    ("QA-ZONE", "Zona de control de calidad"),
    ("PROD-ZONE", "Zona de producción"),
    ("PACK-ZONE", "Zona de empaque"),
]


class MovementOrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Seeds ────────────────────────────────────────────────────────────────
    async def seed_operation_types(self, tenant_id: str) -> list[OperationType]:
        existing = set((await self.db.execute(
            select(OperationType.code).where(OperationType.tenant_id == tenant_id)
        )).scalars().all())
        created = []
        for spec in DEFAULT_OPERATION_TYPES:
            if spec["code"] in existing:
                continue
            obj = OperationType(id=str(uuid.uuid4()), tenant_id=tenant_id, **spec)
            self.db.add(obj)
            created.append(obj)
        await self.db.flush()
        return created

    async def ensure_interim_locations(self, tenant_id: str, warehouse_id: str) -> dict[str, WarehouseLocation]:
        existing = {
            loc.code: loc for loc in (await self.db.execute(
                select(WarehouseLocation).where(
                    WarehouseLocation.tenant_id == tenant_id,
                    WarehouseLocation.warehouse_id == warehouse_id,
                    WarehouseLocation.location_kind == "interim",
                )
            )).scalars().all()
        }
        out: dict[str, WarehouseLocation] = {}
        for code, name in INTERIM_ZONES:
            if code in existing:
                out[code] = existing[code]
                continue
            loc = WarehouseLocation(
                id=str(uuid.uuid4()), tenant_id=tenant_id, warehouse_id=warehouse_id,
                name=name, code=code, location_type="zone", location_kind="interim",
            )
            self.db.add(loc)
            out[code] = loc
        await self.db.flush()
        return out

    # ── Movement orders ──────────────────────────────────────────────────────
    async def create_order(self, tenant_id: str, body: MovementOrderCreate, user_id: str | None) -> TransferOrder:
        seq = await SequenceRepository(self.db).next_value(tenant_id, "wm_movement_order")
        order = TransferOrder(
            id=str(uuid.uuid4()), tenant_id=tenant_id, warehouse_id=body.warehouse_id,
            to_number=f"MO-{seq:06d}",
            operation_type_id=body.operation_type_id, requirement_id=body.requirement_id,
            source_doc_type=body.source_doc_type, source_doc_id=body.source_doc_id,
            notes=body.notes, status="open", created_by=user_id,
        )
        self.db.add(order)
        for i, ln in enumerate(body.lines, start=1):
            self.db.add(TransferOrderLine(
                id=str(uuid.uuid4()), tenant_id=tenant_id, transfer_order_id=order.id,
                line_no=i, product_id=ln.product_id, batch_id=ln.batch_id, variant_id=ln.variant_id,
                quantity=ln.quantity, uom=ln.uom,
                source_location_id=ln.source_location_id, dest_location_id=ln.dest_location_id,
                status="open",
            ))
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def get_order(self, tenant_id: str, order_id: str) -> TransferOrder | None:
        return (await self.db.execute(
            select(TransferOrder).where(
                TransferOrder.tenant_id == tenant_id, TransferOrder.id == order_id,
            )
        )).scalar_one_or_none()

    async def list_lines(self, tenant_id: str, order_id: str) -> list[TransferOrderLine]:
        return list((await self.db.execute(
            select(TransferOrderLine).where(
                TransferOrderLine.tenant_id == tenant_id,
                TransferOrderLine.transfer_order_id == order_id,
            ).order_by(TransferOrderLine.line_no)
        )).scalars().all())

    def _quant_key(self, query, tenant_id, product_id, warehouse_id, batch_id, variant_id, location_id):
        query = query.where(
            StockLevel.tenant_id == tenant_id,
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.location_id == location_id,
        )
        query = query.where(StockLevel.batch_id == batch_id) if batch_id is not None \
            else query.where(StockLevel.batch_id.is_(None))
        query = query.where(StockLevel.variant_id == variant_id) if variant_id is not None \
            else query.where(StockLevel.variant_id.is_(None))
        return query

    async def _move_quant(
        self, tenant_id: str, product_id: str, warehouse_id: str,
        batch_id: str | None, variant_id: str | None,
        source_location_id: str, dest_location_id: str, qty: Decimal,
    ) -> None:
        """Move `qty` of one quant from source bin to dest bin (same warehouse).

        Splits the source quant — only `qty` moves, the remainder stays put —
        and validates the source bin holds enough free (unreserved) stock. A
        no-op when source == dest.
        """
        if source_location_id == dest_location_id:
            return
        src = (await self.db.execute(self._quant_key(
            select(StockLevel), tenant_id, product_id, warehouse_id,
            batch_id, variant_id, source_location_id,
        ).with_for_update())).scalar_one_or_none()
        free = (src.qty_on_hand - src.qty_reserved) if src else Decimal("0")
        if src is None or free < qty:
            raise ValidationError(
                f"Stock insuficiente en el bin de origen: disponible {free}, requerido {qty}"
            )
        src.qty_on_hand -= qty
        dst = (await self.db.execute(self._quant_key(
            select(StockLevel), tenant_id, product_id, warehouse_id,
            batch_id, variant_id, dest_location_id,
        ).with_for_update())).scalar_one_or_none()
        if dst is None:
            self.db.add(StockLevel(
                id=str(uuid.uuid4()), tenant_id=tenant_id, product_id=product_id,
                warehouse_id=warehouse_id, location_id=dest_location_id,
                batch_id=batch_id, variant_id=variant_id,
                qty_on_hand=qty, qty_reserved=Decimal("0"),
                weighted_avg_cost=src.weighted_avg_cost, stock_type=src.stock_type,
            ))
        else:
            dst.qty_on_hand += qty

    async def confirm_line(
        self, tenant_id: str, order_id: str, line_id: str, body: ConfirmLineIn, user_id: str | None,
    ) -> TransferOrderLine:
        order = await self.get_order(tenant_id, order_id)
        if not order:
            raise NotFoundError(f"Movement order {order_id!r} not found")
        if order.status == "canceled":
            raise ValidationError("La orden está cancelada")
        line = (await self.db.execute(
            select(TransferOrderLine).where(
                TransferOrderLine.tenant_id == tenant_id,
                TransferOrderLine.transfer_order_id == order_id,
                TransferOrderLine.id == line_id,
            )
        )).scalar_one_or_none()
        if not line:
            raise NotFoundError(f"Line {line_id!r} not found")

        if body.source_location_id:
            line.source_location_id = body.source_location_id
        if body.dest_location_id:
            line.dest_location_id = body.dest_location_id
        if body.confirmed_qty is not None:
            line.confirmed_qty = body.confirmed_qty
        if body.confirm_source:
            line.source_confirmed = True
        if body.confirm_dest:
            line.dest_confirmed = True

        order.status = "in_progress"

        # Both ends confirmed → execute the move (split quant + kardex).
        if line.source_confirmed and line.dest_confirmed and line.status != "done":
            qty = Decimal(line.confirmed_qty if line.confirmed_qty is not None else line.quantity)
            if not line.source_location_id or not line.dest_location_id:
                raise ValidationError(
                    "La línea requiere bin de origen y destino para ejecutar el movimiento"
                )
            # Move exactly `qty` from source bin to dest bin: splits the source
            # quant (remainder stays put) and validates available stock. Never
            # relocates the whole row, never touches an unrelated quant.
            await self._move_quant(
                tenant_id, line.product_id, order.warehouse_id,
                line.batch_id, line.variant_id,
                line.source_location_id, line.dest_location_id, qty,
            )
            self.db.add(StockMovement(
                id=str(uuid.uuid4()), tenant_id=tenant_id, movement_type="transfer",
                product_id=line.product_id, from_warehouse_id=order.warehouse_id,
                to_warehouse_id=order.warehouse_id, quantity=qty, uom=line.uom,
                reference=order.to_number, batch_id=line.batch_id, variant_id=line.variant_id,
                performed_by=user_id, status="completed",
                completed_at=datetime.now(timezone.utc),
                notes=f"WM {order.to_number} L{line.line_no}",
            ))
            line.status = "done"

        await self.db.flush()

        # Whole order done when every line is done.
        lines = await self.list_lines(tenant_id, order_id)
        if lines and all(ln.status == "done" for ln in lines):
            order.status = "confirmed"
            order.confirmed_at = datetime.now(timezone.utc)
            order.confirmed_by = user_id
            await self.db.flush()

        await self.db.refresh(line)
        return line
