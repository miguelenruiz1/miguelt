"""Business logic for production runs (BOM execution)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models import MovementType
from app.repositories.layer_repo import LayerRepository
from app.repositories.movement_repo import MovementRepository
from app.repositories.production_repo import ProductionRunRepository
from app.repositories.recipe_repo import RecipeRepository
from app.repositories.stock_repo import StockRepository


class ProductionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.recipe_repo = RecipeRepository(db)
        self.run_repo = ProductionRunRepository(db)
        self.stock_repo = StockRepository(db)
        self.movement_repo = MovementRepository(db)
        self.layer_repo = LayerRepository(db)

    # ── Recipes ─────────────────────────────────────────────────────────────

    async def list_recipes(self, tenant_id: str, offset: int = 0, limit: int = 50):
        return await self.recipe_repo.list(tenant_id, offset=offset, limit=limit)

    async def get_recipe(self, tenant_id: str, recipe_id: str):
        r = await self.recipe_repo.get(tenant_id, recipe_id)
        if not r:
            raise NotFoundError("Receta no encontrada")
        return r

    async def create_recipe(self, tenant_id: str, data: dict, components: list[dict]):
        return await self.recipe_repo.create(tenant_id, data, components)

    async def update_recipe(self, tenant_id: str, recipe_id: str, data: dict, components: list[dict] | None = None):
        r = await self.recipe_repo.get(tenant_id, recipe_id)
        if not r:
            raise NotFoundError("Receta no encontrada")
        return await self.recipe_repo.update(r, data, components)

    async def delete_recipe(self, tenant_id: str, recipe_id: str):
        r = await self.recipe_repo.get(tenant_id, recipe_id)
        if not r:
            raise NotFoundError("Receta no encontrada")
        await self.recipe_repo.soft_delete(r)

    # ── Production Runs ─────────────────────────────────────────────────────

    async def list_runs(self, tenant_id: str, status: str | None = None, offset: int = 0, limit: int = 50):
        return await self.run_repo.list(tenant_id, status, offset, limit)

    async def get_run(self, tenant_id: str, run_id: str):
        r = await self.run_repo.get(tenant_id, run_id)
        if not r:
            raise NotFoundError("Orden de producción no encontrada")
        return r

    async def delete_run(self, tenant_id: str, run_id: str) -> None:
        run = await self.run_repo.get(tenant_id, run_id)
        if not run:
            raise NotFoundError("Orden de producción no encontrada")
        if run.status != "pending":
            raise ValidationError(
                f"Solo se pueden eliminar órdenes en estado 'pending', actual: '{run.status}'"
            )
        await self.run_repo.delete(run)

    async def create_run(self, tenant_id: str, data: dict, performed_by: str | None = None):
        recipe = await self.recipe_repo.get(tenant_id, data["recipe_id"])
        if not recipe:
            raise NotFoundError("Receta no encontrada")

        run_number = await self.run_repo.next_run_number(tenant_id)
        return await self.run_repo.create({
            "tenant_id": tenant_id,
            "recipe_id": data["recipe_id"],
            "run_number": run_number,
            "warehouse_id": data["warehouse_id"],
            "multiplier": data.get("multiplier", Decimal("1")),
            "status": "pending",
            "performed_by": performed_by,
            "notes": data.get("notes"),
        })

    async def _validate_stock(self, recipe, run):
        """Validate stock availability for all components. Raises ValidationError if insufficient."""
        multiplier = run.multiplier
        insufficient: list[str] = []
        for comp in recipe.components:
            required_qty = comp.quantity_required * multiplier
            level = await self.stock_repo.get_level(comp.component_entity_id, run.warehouse_id)
            available = level.qty_on_hand if level else Decimal("0")
            if available < required_qty:
                name = getattr(comp.component_entity, "name", None) or comp.component_entity_id[:8]
                insufficient.append(
                    f"• {name}: disponible {available}, requerido {required_qty}"
                )
        if insufficient:
            detail = "\n".join(insufficient)
            raise ValidationError(
                f"Stock insuficiente para {len(insufficient)} componente(s):\n{detail}"
            )

    async def _materialize_production(self, tenant_id: str, run, recipe, performed_by: str | None):
        """Consume components, produce output, create movements and cost layers."""
        multiplier = run.multiplier

        # Consume components
        total_component_cost = Decimal("0")
        for comp in recipe.components:
            required_qty = comp.quantity_required * multiplier
            await self.stock_repo.upsert_level(
                tenant_id, comp.component_entity_id, run.warehouse_id, -required_qty
            )
            cost_consumed = await self.layer_repo.consume_fifo(
                comp.component_entity_id, run.warehouse_id, required_qty
            )
            total_component_cost += cost_consumed
            await self.movement_repo.create({
                "tenant_id": tenant_id,
                "movement_type": MovementType.production_out,
                "product_id": comp.component_entity_id,
                "from_warehouse_id": run.warehouse_id,
                "quantity": required_qty,
                "notes": f"Producción {run.run_number} — consumo de componente",
                "performed_by": performed_by,
            })

        # Produce output — use output_warehouse_id if set, else same warehouse
        output_wh = run.output_warehouse_id or run.warehouse_id
        output_qty = recipe.output_quantity * multiplier
        output_unit_cost = (
            total_component_cost / output_qty if output_qty > 0 else Decimal("0")
        )
        await self.stock_repo.upsert_level(
            tenant_id, recipe.output_entity_id, output_wh, output_qty
        )
        mov = await self.movement_repo.create({
            "tenant_id": tenant_id,
            "movement_type": MovementType.production_in,
            "product_id": recipe.output_entity_id,
            "to_warehouse_id": output_wh,
            "quantity": output_qty,
            "unit_cost": output_unit_cost,
            "notes": f"Producción {run.run_number} — producto terminado",
            "performed_by": performed_by,
        })
        await self.layer_repo.create_layer(
            tenant_id=tenant_id,
            entity_id=recipe.output_entity_id,
            warehouse_id=output_wh,
            quantity=output_qty,
            unit_cost=output_unit_cost,
            movement_id=mov.id,
        )

    async def execute_run(self, tenant_id: str, run_id: str, performed_by: str | None = None):
        """pending → in_progress  (validates stock, marks production as started)."""
        run = await self.run_repo.get(tenant_id, run_id)
        if not run:
            raise NotFoundError("Orden de producción no encontrada")
        if run.status != "pending":
            raise ValidationError(f"La orden está en estado '{run.status}', solo se puede ejecutar desde 'pending'")

        recipe = await self.recipe_repo.get(tenant_id, run.recipe_id)
        if not recipe:
            raise NotFoundError("Receta no encontrada")
        if not recipe.components:
            raise ValidationError("La receta no tiene componentes definidos")

        # Validate stock — no stock is moved yet, only validated
        await self._validate_stock(recipe, run)

        # Mark in_progress — stock stays untouched until supervisor approves
        await self.run_repo.update(run, {
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc),
            "performed_by": performed_by or run.performed_by,
        })

        return await self.run_repo.get(tenant_id, run_id)

    async def finish_run(self, tenant_id: str, run_id: str):
        """in_progress → awaiting_approval  (production finished, pending supervisor review)."""
        run = await self.run_repo.get(tenant_id, run_id)
        if not run:
            raise NotFoundError("Orden de producción no encontrada")
        if run.status != "in_progress":
            raise ValidationError(
                f"Solo se puede finalizar una orden en estado 'in_progress', actual: '{run.status}'"
            )
        await self.run_repo.update(run, {
            "status": "awaiting_approval",
        })
        return await self.run_repo.get(tenant_id, run_id)

    async def approve_run(self, tenant_id: str, run_id: str, approved_by: str | None = None):
        run = await self.run_repo.get(tenant_id, run_id)
        if not run:
            raise NotFoundError("Orden de producción no encontrada")
        if run.status != "awaiting_approval":
            raise ValidationError(
                f"Solo se pueden aprobar órdenes en estado 'awaiting_approval', actual: '{run.status}'"
            )
        if approved_by and run.performed_by and approved_by == run.performed_by:
            raise ValidationError(
                "El ejecutor no puede aprobar su propia corrida de producción (principio de 4 ojos)"
            )

        recipe = await self.recipe_repo.get(tenant_id, run.recipe_id)
        if not recipe:
            raise NotFoundError("Receta no encontrada")

        # Re-validate stock at approval time (may have changed since execute)
        await self._validate_stock(recipe, run)

        # Now actually move stock — consume components + produce output
        await self._materialize_production(tenant_id, run, recipe, run.performed_by)

        await self.run_repo.update(run, {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc),
            "approved_by": approved_by,
            "approved_at": datetime.now(timezone.utc),
        })
        return await self.run_repo.get(tenant_id, run_id)

    async def reject_run(self, tenant_id: str, run_id: str, rejection_notes: str, rejected_by: str | None = None):
        run = await self.run_repo.get(tenant_id, run_id)
        if not run:
            raise NotFoundError("Orden de producción no encontrada")
        if run.status != "awaiting_approval":
            raise ValidationError(
                f"Solo se pueden rechazar órdenes en estado 'awaiting_approval', actual: '{run.status}'"
            )
        await self.run_repo.update(run, {
            "status": "rejected",
            "rejection_notes": rejection_notes,
            "updated_by": rejected_by,
        })
        return await self.run_repo.get(tenant_id, run_id)
