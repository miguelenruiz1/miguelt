"""Stock reservation service for Sales Orders.

Manages the lifecycle of stock reservations:
  confirm  → reserve_for_so()  → StockReservation(active), qty_reserved += qty
  deliver  → consume_for_so()  → StockReservation(consumed), qty_on_hand -= qty, qty_reserved -= qty
  cancel   → release_for_so()  → StockReservation(released), qty_reserved -= qty
  return   → (no reservation change — stock restocked separately)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import SalesOrder, SalesOrderLine, StockLevel
from app.db.models.stock import StockReservation


class InsufficientStockError(Exception):
    def __init__(self, product_name: str, warehouse_name: str, available: float, required: float):
        self.product_name = product_name
        self.warehouse_name = warehouse_name
        self.available = available
        self.required = required
        super().__init__(
            f"Stock insuficiente para \"{product_name}\" en \"{warehouse_name}\". "
            f"Disponible: {available}, Requerido: {required}"
        )


class ReservationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def reserve_for_so(
        self,
        so: SalesOrder,
        tenant_id: str,
    ) -> list[StockReservation]:
        """Reserve stock for all lines of a confirmed SO.

        Atomic: if any line fails, the transaction should be rolled back by the caller.
        Creates StockReservation records and increments qty_reserved on StockLevel.
        """
        from app.repositories.stock_repo import StockRepository

        stock_repo = StockRepository(self.db)
        reservations: list[StockReservation] = []

        for line in so.lines:
            eff_wh = line.warehouse_id or so.warehouse_id
            if not eff_wh:
                product_name = line.product.name if line.product else line.product_id
                raise ValueError(
                    f"No se puede reservar stock para '{product_name}': no tiene bodega asignada."
                )
            qty = Decimal(str(line.qty_ordered))
            if qty <= 0:
                continue

            # Atomic reserve via repo (validates availability)
            try:
                await stock_repo.reserve(line.product_id, eff_wh, qty, variant_id=line.variant_id)
            except ValueError:
                # Enrich error with detailed availability info
                avail = await stock_repo.get_available_stock(tenant_id, line.product_id, eff_wh)
                product_name = line.product.name if line.product else line.product_id
                raise ValueError(
                    f"Producto '{product_name}': disponible {avail['qty_available']} unidades "
                    f"({avail['qty_on_hand']} en bodega - {avail['qty_reserved']} reservadas), "
                    f"solicitadas {float(qty)}"
                )

            reservation = StockReservation(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                sales_order_id=so.id,
                sales_order_line_id=line.id,
                product_id=line.product_id,
                variant_id=line.variant_id,
                warehouse_id=eff_wh,
                quantity=qty,
                status="active",
            )
            self.db.add(reservation)
            reservations.append(reservation)

        await self.db.flush()
        return reservations

    async def release_for_so(
        self,
        so_id: str,
        tenant_id: str,
        reason: str,
    ) -> None:
        """Release all active reservations for a SO (cancel)."""
        from app.repositories.stock_repo import StockRepository

        stock_repo = StockRepository(self.db)
        result = await self.db.execute(
            select(StockReservation).where(
                StockReservation.sales_order_id == so_id,
                StockReservation.status == "active",
            )
        )
        now = datetime.now(timezone.utc)
        for reservation in result.scalars():
            await stock_repo.release_reservation(
                reservation.product_id,
                reservation.warehouse_id,
                reservation.quantity,
                variant_id=reservation.variant_id,
            )
            reservation.status = "released"
            reservation.released_at = now
            reservation.released_reason = reason

        await self.db.flush()

    async def consume_for_so(
        self,
        so: SalesOrder,
        tenant_id: str,
    ) -> bool:
        """Consume reservations at delivery: release reserved qty and mark as consumed.

        Stock deduction (qty_on_hand) is handled separately by the caller (deliver)
        to support batch-aware dispatch (FEFO).

        Returns True if reservations were found and consumed, False otherwise
        (backward compat: old orders without reservations).
        """
        from app.repositories.stock_repo import StockRepository

        stock_repo = StockRepository(self.db)

        result = await self.db.execute(
            select(StockReservation).where(
                StockReservation.sales_order_id == so.id,
                StockReservation.status == "active",
            )
        )
        reservations = list(result.scalars())
        if not reservations:
            return False  # No reservations (old order — stock already deducted at ship)

        now = datetime.now(timezone.utc)
        for reservation in reservations:
            # Release reserved qty
            await stock_repo.release_reservation(
                reservation.product_id, reservation.warehouse_id,
                reservation.quantity, variant_id=reservation.variant_id,
            )
            reservation.status = "consumed"
            reservation.released_at = now
            reservation.released_reason = "delivered"

        await self.db.flush()
        return True

    async def get_so_reservations(self, so_id: str) -> list[StockReservation]:
        """List all reservations for a SO with product/warehouse details."""
        result = await self.db.execute(
            select(StockReservation)
            .where(StockReservation.sales_order_id == so_id)
            .options(
                joinedload(StockReservation.product),
                joinedload(StockReservation.warehouse),
            )
            .order_by(StockReservation.reserved_at)
        )
        return list(result.scalars().unique().all())
