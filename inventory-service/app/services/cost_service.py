"""Cost layering service (FIFO)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.layer_repo import LayerRepository


class CostService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.layer_repo = LayerRepository(db)

    async def create_layer(
        self,
        tenant_id: str,
        entity_id: str,
        warehouse_id: str,
        quantity: Decimal,
        unit_cost: Decimal,
        movement_id: str | None = None,
        batch_id: str | None = None,
    ):
        return await self.layer_repo.create_layer(
            tenant_id, entity_id, warehouse_id, quantity, unit_cost, movement_id, batch_id
        )

    async def consume_fifo(
        self, entity_id: str, warehouse_id: str, quantity: Decimal
    ) -> Decimal:
        return await self.layer_repo.consume_fifo(entity_id, warehouse_id, quantity)

    async def get_weighted_average_cost(
        self, entity_id: str, warehouse_id: str
    ) -> Decimal:
        return await self.layer_repo.get_weighted_average_cost(entity_id, warehouse_id)

    async def list_layers(
        self, tenant_id: str, entity_id: str, warehouse_id: str | None = None
    ):
        return await self.layer_repo.list_layers(tenant_id, entity_id, warehouse_id)
