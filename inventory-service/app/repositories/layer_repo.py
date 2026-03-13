"""Repository for StockLayer (FIFO cost layering)."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StockLayer


class LayerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_layer(
        self,
        tenant_id: str,
        entity_id: str,
        warehouse_id: str,
        quantity: Decimal,
        unit_cost: Decimal,
        movement_id: str | None = None,
        batch_id: str | None = None,
    ) -> StockLayer:
        layer = StockLayer(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            entity_id=entity_id,
            warehouse_id=warehouse_id,
            movement_id=movement_id,
            quantity_initial=quantity,
            quantity_remaining=quantity,
            unit_cost=unit_cost,
            batch_id=batch_id,
        )
        self.db.add(layer)
        await self.db.flush()
        await self.db.refresh(layer)
        return layer

    async def consume_fifo(
        self,
        entity_id: str,
        warehouse_id: str,
        quantity: Decimal,
    ) -> Decimal:
        """Consume from oldest layers first. Returns total cost consumed."""
        result = await self.db.execute(
            select(StockLayer)
            .where(
                StockLayer.entity_id == entity_id,
                StockLayer.warehouse_id == warehouse_id,
                StockLayer.quantity_remaining > 0,
            )
            .order_by(StockLayer.created_at.asc())
            .with_for_update()
        )
        layers = list(result.scalars().all())
        remaining = quantity
        total_cost = Decimal("0")
        for layer in layers:
            if remaining <= 0:
                break
            consume = min(remaining, layer.quantity_remaining)
            total_cost += consume * layer.unit_cost
            layer.quantity_remaining -= consume
            remaining -= consume
        await self.db.flush()
        return total_cost

    async def get_weighted_average_cost(
        self, entity_id: str, warehouse_id: str
    ) -> Decimal:
        result = await self.db.execute(
            select(StockLayer)
            .where(
                StockLayer.entity_id == entity_id,
                StockLayer.warehouse_id == warehouse_id,
                StockLayer.quantity_remaining > 0,
            )
        )
        layers = list(result.scalars().all())
        total_qty = sum(l.quantity_remaining for l in layers)
        if total_qty <= 0:
            return Decimal("0")
        total_value = sum(l.quantity_remaining * l.unit_cost for l in layers)
        return total_value / total_qty

    async def list_layers(
        self, tenant_id: str, entity_id: str, warehouse_id: str | None = None
    ) -> list[StockLayer]:
        q = select(StockLayer).where(
            StockLayer.tenant_id == tenant_id,
            StockLayer.entity_id == entity_id,
        )
        if warehouse_id:
            q = q.where(StockLayer.warehouse_id == warehouse_id)
        q = q.order_by(StockLayer.created_at.asc())
        result = await self.db.execute(q)
        return list(result.scalars().all())
