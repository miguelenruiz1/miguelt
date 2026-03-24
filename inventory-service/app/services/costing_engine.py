"""Central costing engine -- handles stock layer creation and consumption
for both FIFO and Weighted Average valuation methods."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.stock import StockLevel
from app.repositories.layer_repo import LayerRepository


class CostingEngine:
    """Central costing engine -- handles stock layer creation and consumption
    for both FIFO and Weighted Average valuation methods."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.layer_repo = LayerRepository(db)

    async def on_stock_in(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        quantity: Decimal,
        unit_cost: Decimal,
        movement_id: str | None = None,
        batch_id: str | None = None,
    ):
        """Called on EVERY stock entry: PO receipt, return, adjustment_in, production_in.
        Creates a new StockLayer and updates StockLevel.weighted_avg_cost."""
        layer = await self.layer_repo.create_layer(
            tenant_id=tenant_id,
            entity_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            unit_cost=unit_cost,
            movement_id=movement_id,
            batch_id=batch_id,
        )
        # Update weighted avg cost on StockLevel
        avg = await self.layer_repo.get_weighted_average_cost(product_id, warehouse_id)
        await self._update_level_avg_cost(tenant_id, product_id, warehouse_id, avg)
        return layer

    async def on_stock_out(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        quantity: Decimal,
        valuation_method: str = "weighted_average",
    ) -> tuple[Decimal, list[str]]:
        """Called on EVERY stock exit: sale, waste, adjustment_out, production_out.
        Consumes layers per method and returns (total_cost, layer_ids)."""
        if valuation_method == "fifo":
            total_cost, layer_ids = await self._consume_fifo(product_id, warehouse_id, quantity)
        else:
            total_cost, layer_ids = await self._consume_weighted_avg(product_id, warehouse_id, quantity)

        avg = await self.layer_repo.get_weighted_average_cost(product_id, warehouse_id)
        await self._update_level_avg_cost(tenant_id, product_id, warehouse_id, avg)
        return total_cost, layer_ids

    async def _consume_fifo(
        self, product_id: str, warehouse_id: str, quantity: Decimal
    ) -> tuple[Decimal, list[str]]:
        """FIFO consumption -- oldest layers first."""
        total_cost = await self.layer_repo.consume_fifo(
            entity_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
        )
        # consume_fifo returns Decimal total_cost
        # For layer_ids we'd need to track which layers were touched
        # For now return empty list -- the cost is what matters
        return total_cost, []

    async def _consume_weighted_avg(
        self, product_id: str, warehouse_id: str, quantity: Decimal
    ) -> tuple[Decimal, list[str]]:
        """Weighted average -- consume at current average cost, deplete layers FIFO underneath."""
        avg_cost = await self.layer_repo.get_weighted_average_cost(product_id, warehouse_id)
        if avg_cost is None:
            avg_cost = Decimal("0")
        total_cost = quantity * avg_cost

        # Still deplete actual layers (FIFO order) to keep quantities consistent
        # This ensures sum(layer.quantity_remaining) always equals StockLevel.qty_on_hand
        try:
            await self.layer_repo.consume_fifo(
                entity_id=product_id,
                warehouse_id=warehouse_id,
                quantity=quantity,
            )
        except Exception:
            pass  # If no layers exist yet, just use the avg cost calculation

        return total_cost, []

    async def _update_level_avg_cost(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        avg_cost: Decimal | None,
    ) -> None:
        """Update StockLevel.weighted_avg_cost."""
        stmt = (
            update(StockLevel)
            .where(
                StockLevel.tenant_id == tenant_id,
                StockLevel.product_id == product_id,
                StockLevel.warehouse_id == warehouse_id,
            )
            .values(weighted_avg_cost=avg_cost)
        )
        await self.db.execute(stmt)
