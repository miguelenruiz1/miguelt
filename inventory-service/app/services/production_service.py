"""Production v2 — BOM execution with discrete emission/receipt documents.

Flow: planned → released (reserve) → in_progress (emission) → completed (receipt) → closed (variance)
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import update as sa_update

from app.core.errors import NotFoundError, ValidationError
from app.db.models import MovementType
from app.db.models.production import EntityRecipe
from app.repositories.emission_repo import EmissionRepository
from app.repositories.layer_repo import LayerRepository
from app.repositories.movement_repo import MovementRepository
from app.repositories.production_repo import ProductionRunRepository
from app.repositories.receipt_repo import ReceiptRepository
from app.repositories.recipe_repo import RecipeRepository
from app.repositories.resource_repo import ResourceRepository
from app.repositories.stock_repo import StockRepository


class ProductionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.recipe_repo = RecipeRepository(db)
        self.run_repo = ProductionRunRepository(db)
        self.stock_repo = StockRepository(db)
        self.movement_repo = MovementRepository(db)
        self.layer_repo = LayerRepository(db)
        self.emission_repo = EmissionRepository(db)
        self.receipt_repo = ReceiptRepository(db)
        self.resource_repo = ResourceRepository(db)

    # ── Recipes ────────────────────────────────────────────────────────────────

    async def list_recipes(self, tenant_id: str, offset: int = 0, limit: int = 50):
        return await self.recipe_repo.list(tenant_id, offset=offset, limit=limit)

    async def get_recipe(self, tenant_id: str, recipe_id: str):
        r = await self.recipe_repo.get(tenant_id, recipe_id)
        if not r:
            raise NotFoundError("Receta no encontrada")
        return r

    async def create_recipe(self, tenant_id: str, data: dict, components: list[dict]):
        recipe = await self.recipe_repo.create(tenant_id, data, components)
        await self._recalculate_standard_cost(recipe)
        return await self.recipe_repo.get(tenant_id, recipe.id)

    async def update_recipe(self, tenant_id: str, recipe_id: str, data: dict, components: list[dict] | None = None):
        r = await self.recipe_repo.get(tenant_id, recipe_id)
        if not r:
            raise NotFoundError("Receta no encontrada")
        updated = await self.recipe_repo.update(r, data, components)
        await self._recalculate_standard_cost(updated)
        return await self.recipe_repo.get(tenant_id, recipe_id)

    async def _recalculate_standard_cost(self, recipe):
        """Auto-calculate standard_cost from component costs + resource costs."""
        total_cost = Decimal("0")
        # Component costs
        for comp in (recipe.components or []):
            scrap_factor = Decimal("1") + (comp.scrap_percentage or Decimal("0")) / Decimal("100")
            qty = comp.quantity_required * scrap_factor
            avg_cost = await self.layer_repo.weighted_avg_cost(comp.component_entity_id)
            total_cost += qty * avg_cost
        # Resource costs (per unit of output)
        for res in (recipe.resources or []):
            resource = res.resource
            if resource:
                total_cost += res.hours_per_unit * resource.cost_per_hour
                # Amortize setup over planned production size
                if res.setup_time_hours > 0 and recipe.planned_production_size > 0:
                    total_cost += (res.setup_time_hours * resource.cost_per_hour) / Decimal(str(recipe.planned_production_size))
        if total_cost != (recipe.standard_cost or Decimal("0")):
            await self.db.execute(
                sa_update(EntityRecipe)
                .where(EntityRecipe.id == recipe.id)
                .values(standard_cost=total_cost)
            )
            await self.db.flush()

    async def delete_recipe(self, tenant_id: str, recipe_id: str):
        r = await self.recipe_repo.get(tenant_id, recipe_id)
        if not r:
            raise NotFoundError("Receta no encontrada")
        await self.recipe_repo.soft_delete(r)

    # ── Production Runs — CRUD ─────────────────────────────────────────────────

    async def list_runs(self, tenant_id: str, status: str | None = None, offset: int = 0, limit: int = 50):
        return await self.run_repo.list(tenant_id, status, offset, limit)

    async def get_run(self, tenant_id: str, run_id: str):
        r = await self.run_repo.get(tenant_id, run_id)
        if not r:
            raise NotFoundError("Orden de produccion no encontrada")
        return r

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
            "output_warehouse_id": data.get("output_warehouse_id"),
            "multiplier": data.get("multiplier", Decimal("1")),
            "status": "planned",
            "performed_by": performed_by,
            "notes": data.get("notes"),
            "order_type": data.get("order_type", "standard"),
            "priority": data.get("priority", 50),
            "planned_start_date": data.get("planned_start_date"),
            "planned_end_date": data.get("planned_end_date"),
            "linked_sales_order_id": data.get("linked_sales_order_id"),
            "linked_customer_id": data.get("linked_customer_id"),
        })

    async def update_run(self, tenant_id: str, run_id: str, data: dict):
        run = await self._get_run_or_404(tenant_id, run_id)
        if run.status != "planned":
            raise ValidationError("Solo se pueden editar ordenes en estado 'planned'")
        await self.run_repo.update(run, {k: v for k, v in data.items() if v is not None})
        return await self.run_repo.get(tenant_id, run_id)

    async def delete_run(self, tenant_id: str, run_id: str) -> None:
        run = await self._get_run_or_404(tenant_id, run_id)
        if run.status != "planned":
            raise ValidationError(f"Solo se pueden eliminar ordenes en estado 'planned', actual: '{run.status}'")
        await self.run_repo.delete(run)

    # ── Release (planned → released) ─────────────────────────────────────────

    async def release_run(self, tenant_id: str, run_id: str, performed_by: str | None = None):
        """Reserve stock and mark order as released. For disassembly, reserves output product."""
        run = await self._get_run_or_404(tenant_id, run_id)
        if run.status != "planned":
            raise ValidationError(f"Solo se puede liberar desde 'planned', actual: '{run.status}'")

        recipe = await self._get_recipe_or_404(tenant_id, run.recipe_id)
        if not recipe.components:
            raise ValidationError("La receta no tiene componentes definidos")

        multiplier = run.multiplier
        is_disassembly = run.order_type == "disassembly"

        if is_disassembly:
            # Disassembly: reserve the OUTPUT product (we'll take it apart)
            output_qty = recipe.output_quantity * multiplier
            output_wh = run.output_warehouse_id or run.warehouse_id
            level = await self.stock_repo.get_level(recipe.output_entity_id, output_wh)
            available = (level.qty_on_hand - level.qty_reserved) if level else Decimal("0")
            if available < output_qty:
                raise ValidationError(f"Stock insuficiente del producto a desmontar: disponible {available}, requerido {output_qty}")
            await self.stock_repo.reserve(recipe.output_entity_id, output_wh, output_qty)
        else:
            # Standard: reserve components
            for comp in recipe.components:
                scrap_factor = Decimal("1") + comp.scrap_percentage / Decimal("100")
                required_qty = comp.quantity_required * multiplier * scrap_factor
                level = await self.stock_repo.get_level(comp.component_entity_id, run.warehouse_id)
                available = (level.qty_on_hand - level.qty_reserved) if level else Decimal("0")
                if available < required_qty:
                    name = getattr(comp.component_entity, "name", None) or comp.component_entity_id[:8]
                    raise ValidationError(f"Stock insuficiente para {name}: disponible {available}, requerido {required_qty}")
                await self.stock_repo.reserve(comp.component_entity_id, run.warehouse_id, required_qty)

        # Create planned resource costs
        import uuid as _uuid
        from app.db.models.production import ProductionRunResourceCost
        total_resource_cost = Decimal("0")
        for res in (recipe.resources or []):
            resource = res.resource
            if not resource:
                continue
            planned_hrs = (res.hours_per_unit * recipe.output_quantity * multiplier) + res.setup_time_hours
            cost = planned_hrs * resource.cost_per_hour
            total_resource_cost += cost
            rc = ProductionRunResourceCost(
                id=str(_uuid.uuid4()),
                production_run_id=run.id,
                resource_id=resource.id,
                planned_hours=planned_hrs,
                cost_per_hour=resource.cost_per_hour,
                total_cost=cost,
            )
            self.db.add(rc)

        await self.run_repo.update(run, {
            "status": "released",
            "performed_by": performed_by or run.performed_by,
            "total_resource_cost": total_resource_cost if total_resource_cost > 0 else None,
        })
        return await self.run_repo.get(tenant_id, run_id)

    # ── Cancel (planned|released → canceled) ─────────────────────────────────

    async def cancel_run(self, tenant_id: str, run_id: str):
        """Cancel order and release any reservations."""
        run = await self._get_run_or_404(tenant_id, run_id)
        if run.status not in ("planned", "released"):
            raise ValidationError(f"Solo se puede cancelar desde 'planned' o 'released', actual: '{run.status}'")

        # Release reservations if was released
        if run.status == "released":
            recipe = await self._get_recipe_or_404(tenant_id, run.recipe_id)
            multiplier = run.multiplier
            if run.order_type == "disassembly":
                output_qty = recipe.output_quantity * multiplier
                output_wh = run.output_warehouse_id or run.warehouse_id
                await self.stock_repo.release_reservation(recipe.output_entity_id, output_wh, output_qty)
            else:
                for comp in recipe.components:
                    scrap_factor = Decimal("1") + comp.scrap_percentage / Decimal("100")
                    reserved_qty = comp.quantity_required * multiplier * scrap_factor
                    await self.stock_repo.release_reservation(comp.component_entity_id, run.warehouse_id, reserved_qty)

        await self.run_repo.update(run, {"status": "canceled"})
        return await self.run_repo.get(tenant_id, run_id)

    # ── Emission (released → in_progress) ────────────────────────────────────

    async def create_emission(self, tenant_id: str, run_id: str, data: dict, performed_by: str | None = None):
        """Issue materials from inventory → WIP. For disassembly, issues the output product instead of components."""
        run = await self._get_run_or_404(tenant_id, run_id)
        if run.status not in ("released", "in_progress"):
            raise ValidationError(f"Solo se puede emitir desde 'released' o 'in_progress', actual: '{run.status}'")

        recipe = await self._get_recipe_or_404(tenant_id, run.recipe_id)

        # Disassembly: emit the OUTPUT product (take it apart)
        if run.order_type == "disassembly":
            return await self._create_disassembly_emission(tenant_id, run, recipe, data, performed_by)

        # Standard/special: emit components
        multiplier = run.multiplier
        wh_id = data.get("warehouse_id") or run.warehouse_id
        now = datetime.now(timezone.utc)
        emission_date = data.get("emission_date") or now

        # Determine lines: from input or auto from BOM
        input_lines = data.get("lines")
        already_emitted = await self.emission_repo.total_emitted_by_component(run_id)

        emission_lines = []
        for comp in recipe.components:
            scrap_factor = Decimal("1") + comp.scrap_percentage / Decimal("100")
            planned_qty = comp.quantity_required * multiplier * scrap_factor
            prev_emitted = Decimal(str(already_emitted.get(comp.component_entity_id, 0)))
            remaining = planned_qty - prev_emitted

            if remaining <= 0:
                continue

            # Find matching input line or use remaining as default
            actual_qty = remaining
            batch_id = None
            line_wh = wh_id
            if input_lines:
                match = next((l for l in input_lines if l.get("component_entity_id") == comp.component_entity_id), None)
                if match:
                    actual_qty = Decimal(str(match["actual_quantity"]))
                    batch_id = match.get("batch_id")
                    line_wh = match.get("warehouse_id") or wh_id

            if actual_qty <= 0:
                continue

            # Validate stock
            level = await self.stock_repo.get_level(comp.component_entity_id, line_wh)
            on_hand = level.qty_on_hand if level else Decimal("0")
            if on_hand < actual_qty:
                name = getattr(comp.component_entity, "name", None) or comp.component_entity_id[:8]
                raise ValidationError(f"Stock insuficiente para {name}: disponible {on_hand}, requerido {actual_qty}")

            # Consume stock
            await self.stock_repo.upsert_level(tenant_id, comp.component_entity_id, line_wh, -actual_qty)
            cost_consumed = await self.layer_repo.consume_fifo(comp.component_entity_id, line_wh, actual_qty)
            unit_cost = cost_consumed / actual_qty if actual_qty > 0 else Decimal("0")

            # Release reservation (if was reserved at release time)
            if run.status == "released" or prev_emitted == 0:
                try:
                    await self.stock_repo.release_reservation(comp.component_entity_id, line_wh, actual_qty)
                except Exception:
                    pass  # reservation may not exist for partial emissions

            # Create stock movement
            await self.movement_repo.create({
                "tenant_id": tenant_id,
                "movement_type": MovementType.production_out,
                "product_id": comp.component_entity_id,
                "from_warehouse_id": line_wh,
                "quantity": actual_qty,
                "unit_cost": unit_cost,
                "notes": f"Emision {run.run_number} — componente",
                "performed_by": performed_by,
            })

            emission_lines.append({
                "component_entity_id": comp.component_entity_id,
                "planned_quantity": planned_qty - prev_emitted,
                "actual_quantity": actual_qty,
                "unit_cost": unit_cost,
                "total_cost": cost_consumed,
                "batch_id": batch_id,
                "warehouse_id": line_wh,
                "variance_quantity": actual_qty - (planned_qty - prev_emitted),
            })

        if not emission_lines:
            raise ValidationError("No hay componentes pendientes de emitir")

        emission_number = await self.emission_repo.next_emission_number(tenant_id)
        emission = await self.emission_repo.create(
            tenant_id=tenant_id,
            production_run_id=run_id,
            emission_number=emission_number,
            emission_date=emission_date,
            warehouse_id=wh_id,
            notes=data.get("notes"),
            performed_by=performed_by,
            lines=emission_lines,
        )

        # Transition to in_progress on first emission
        if run.status == "released":
            await self.run_repo.update(run, {
                "status": "in_progress",
                "actual_start_date": now,
                "started_at": now,
            })

        return await self.emission_repo.get(tenant_id, emission.id)

    async def _create_disassembly_emission(self, tenant_id, run, recipe, data, performed_by):
        """Disassembly emission: take the finished product OUT of inventory."""
        multiplier = run.multiplier
        now = datetime.now(timezone.utc)
        output_wh = run.output_warehouse_id or run.warehouse_id
        output_qty = recipe.output_quantity * multiplier

        # Validate stock of output product
        level = await self.stock_repo.get_level(recipe.output_entity_id, output_wh)
        on_hand = level.qty_on_hand if level else Decimal("0")
        if on_hand < output_qty:
            raise ValidationError(f"Stock insuficiente del producto a desmontar: disponible {on_hand}, requerido {output_qty}")

        # Remove output product from inventory
        await self.stock_repo.upsert_level(tenant_id, recipe.output_entity_id, output_wh, -output_qty)
        cost_consumed = await self.layer_repo.consume_fifo(recipe.output_entity_id, output_wh, output_qty)
        unit_cost = cost_consumed / output_qty if output_qty > 0 else Decimal("0")

        # Release reservation
        try:
            await self.stock_repo.release_reservation(recipe.output_entity_id, output_wh, output_qty)
        except Exception:
            pass

        # Create stock movement
        await self.movement_repo.create({
            "tenant_id": tenant_id,
            "movement_type": MovementType.production_out,
            "product_id": recipe.output_entity_id,
            "from_warehouse_id": output_wh,
            "quantity": output_qty,
            "unit_cost": unit_cost,
            "notes": f"Desmontaje {run.run_number} — producto a desarmar",
            "performed_by": performed_by,
        })

        emission_number = await self.emission_repo.next_emission_number(tenant_id)
        emission = await self.emission_repo.create(
            tenant_id=tenant_id,
            production_run_id=run.id,
            emission_number=emission_number,
            emission_date=data.get("emission_date") or now,
            warehouse_id=output_wh,
            notes=data.get("notes") or "Desmontaje — producto emitido para desarme",
            performed_by=performed_by,
            lines=[{
                "component_entity_id": recipe.output_entity_id,
                "planned_quantity": output_qty,
                "actual_quantity": output_qty,
                "unit_cost": unit_cost,
                "total_cost": cost_consumed,
                "warehouse_id": output_wh,
                "variance_quantity": Decimal("0"),
            }],
        )

        if run.status == "released":
            await self.run_repo.update(run, {
                "status": "in_progress",
                "actual_start_date": now,
                "started_at": now,
                "total_component_cost": cost_consumed,
            })

        return await self.emission_repo.get(tenant_id, emission.id)

    # ── Receipt (in_progress → completed) ────────────────────────────────────

    async def create_receipt(self, tenant_id: str, run_id: str, data: dict, performed_by: str | None = None):
        """Receive finished goods (or components for disassembly) from WIP → inventory."""
        run = await self._get_run_or_404(tenant_id, run_id)
        if run.status != "in_progress":
            raise ValidationError(f"Solo se puede recibir en estado 'in_progress', actual: '{run.status}'")

        recipe = await self._get_recipe_or_404(tenant_id, run.recipe_id)

        # Disassembly: receipt returns COMPONENTS to inventory
        if run.order_type == "disassembly":
            return await self._create_disassembly_receipt(tenant_id, run, recipe, data, performed_by)

        multiplier = run.multiplier
        planned_output = recipe.output_quantity * multiplier
        already_received = await self.receipt_repo.total_received(run_id)
        remaining_output = planned_output - Decimal(str(already_received))

        if remaining_output <= 0:
            raise ValidationError("Ya se recibio la totalidad de la produccion planificada")

        now = datetime.now(timezone.utc)
        receipt_date = data.get("receipt_date") or now
        output_wh = data.get("output_warehouse_id") or run.output_warehouse_id or run.warehouse_id

        # Determine received quantity
        input_lines = data.get("lines")
        if input_lines and len(input_lines) > 0:
            received_qty = Decimal(str(input_lines[0].get("received_quantity", remaining_output)))
            batch_id = input_lines[0].get("batch_id")
            is_complete = input_lines[0].get("is_complete", True)
        else:
            received_qty = remaining_output
            batch_id = None
            is_complete = True

        if received_qty > remaining_output:
            raise ValidationError(f"Cantidad recibida ({received_qty}) excede lo pendiente ({remaining_output})")

        # Calculate unit cost from total component cost of all emissions
        total_component_cost = Decimal(str(await self.emission_repo.total_component_cost(run_id)))
        total_received_after = Decimal(str(already_received)) + received_qty
        unit_cost = total_component_cost / total_received_after if total_received_after > 0 else Decimal("0")
        total_cost = unit_cost * received_qty

        # Add to inventory
        await self.stock_repo.upsert_level(tenant_id, recipe.output_entity_id, output_wh, received_qty)
        mov = await self.movement_repo.create({
            "tenant_id": tenant_id,
            "movement_type": MovementType.production_in,
            "product_id": recipe.output_entity_id,
            "to_warehouse_id": output_wh,
            "quantity": received_qty,
            "unit_cost": unit_cost,
            "notes": f"Recibo {run.run_number} — producto terminado",
            "performed_by": performed_by,
        })

        # Create cost layer
        await self.layer_repo.create_layer(
            tenant_id=tenant_id,
            entity_id=recipe.output_entity_id,
            warehouse_id=output_wh,
            quantity=received_qty,
            unit_cost=unit_cost,
            movement_id=mov.id,
            batch_id=batch_id,
        )

        receipt_number = await self.receipt_repo.next_receipt_number(tenant_id)
        receipt = await self.receipt_repo.create(
            tenant_id=tenant_id,
            production_run_id=run_id,
            receipt_number=receipt_number,
            receipt_date=receipt_date,
            output_warehouse_id=output_wh,
            notes=data.get("notes"),
            performed_by=performed_by,
            lines=[{
                "entity_id": recipe.output_entity_id,
                "planned_quantity": remaining_output,
                "received_quantity": received_qty,
                "unit_cost": unit_cost,
                "total_cost": total_cost,
                "batch_id": batch_id,
                "is_complete": is_complete,
            }],
        )

        # Update run costs (materials + resources)
        actual_output = Decimal(str(already_received)) + received_qty
        resource_cost = run.total_resource_cost or Decimal("0")
        total_production = total_component_cost + resource_cost
        final_unit_cost = total_production / actual_output if actual_output > 0 else Decimal("0")
        await self.run_repo.update(run, {
            "actual_output_quantity": actual_output,
            "total_component_cost": total_component_cost,
            "total_production_cost": total_production,
            "unit_production_cost": final_unit_cost,
        })

        # Transition to completed if all received
        if is_complete or actual_output >= planned_output:
            await self.run_repo.update(run, {
                "status": "completed",
                "actual_end_date": now,
                "completed_at": now,
            })
            # Emit webhook
            from app.clients.webhook_client import emit_event
            await emit_event("production.run.completed", tenant_id, {
                "run_id": run.id, "run_number": run.run_number,
                "actual_output": float(actual_output), "total_cost": float(total_production),
            })

        return await self.receipt_repo.get(tenant_id, receipt.id)

    async def _create_disassembly_receipt(self, tenant_id, run, recipe, data, performed_by):
        """Disassembly receipt: return COMPONENTS to inventory from the disassembled product."""
        multiplier = run.multiplier
        now = datetime.now(timezone.utc)
        wh_id = data.get("output_warehouse_id") or run.warehouse_id
        total_emission_cost = Decimal(str(await self.emission_repo.total_component_cost(run.id)))

        receipt_lines = []
        total_received_cost = Decimal("0")
        for comp in recipe.components:
            comp_qty = comp.quantity_required * multiplier
            # Distribute cost proportionally to component quantities
            unit_cost = total_emission_cost / (recipe.output_quantity * multiplier) * comp.quantity_required if recipe.output_quantity > 0 else Decimal("0")
            line_cost = unit_cost * multiplier

            # Add components back to inventory
            await self.stock_repo.upsert_level(tenant_id, comp.component_entity_id, wh_id, comp_qty)
            mov = await self.movement_repo.create({
                "tenant_id": tenant_id,
                "movement_type": MovementType.production_in,
                "product_id": comp.component_entity_id,
                "to_warehouse_id": wh_id,
                "quantity": comp_qty,
                "unit_cost": unit_cost,
                "notes": f"Desmontaje {run.run_number} — componente recuperado",
                "performed_by": performed_by,
            })
            await self.layer_repo.create_layer(
                tenant_id=tenant_id,
                entity_id=comp.component_entity_id,
                warehouse_id=wh_id,
                quantity=comp_qty,
                unit_cost=unit_cost,
                movement_id=mov.id,
            )
            total_received_cost += line_cost
            receipt_lines.append({
                "entity_id": comp.component_entity_id,
                "planned_quantity": comp_qty,
                "received_quantity": comp_qty,
                "unit_cost": unit_cost,
                "total_cost": line_cost,
                "is_complete": True,
            })

        receipt_number = await self.receipt_repo.next_receipt_number(tenant_id)
        receipt = await self.receipt_repo.create(
            tenant_id=tenant_id,
            production_run_id=run.id,
            receipt_number=receipt_number,
            receipt_date=data.get("receipt_date") or now,
            output_warehouse_id=wh_id,
            notes=data.get("notes") or "Desmontaje — componentes recuperados",
            performed_by=performed_by,
            lines=receipt_lines,
        )

        total_components = len(recipe.components)
        await self.run_repo.update(run, {
            "status": "completed",
            "actual_end_date": now,
            "completed_at": now,
            "actual_output_quantity": Decimal(str(total_components)) * multiplier,
            "total_component_cost": total_emission_cost,
            "total_production_cost": total_emission_cost,
            "unit_production_cost": total_emission_cost / (recipe.output_quantity * multiplier) if recipe.output_quantity > 0 else Decimal("0"),
        })

        return await self.receipt_repo.get(tenant_id, receipt.id)

    # ── Close (completed → closed) ───────────────────────────────────────────

    async def close_run(self, tenant_id: str, run_id: str):
        """Close order and calculate variance."""
        run = await self._get_run_or_404(tenant_id, run_id)
        if run.status != "completed":
            raise ValidationError(f"Solo se puede cerrar desde 'completed', actual: '{run.status}'")

        recipe = await self._get_recipe_or_404(tenant_id, run.recipe_id)
        planned_output = recipe.output_quantity * run.multiplier
        actual_output = run.actual_output_quantity or Decimal("0")
        total_cost = run.total_production_cost or Decimal("0")
        standard_cost = recipe.standard_cost * actual_output if recipe.standard_cost else Decimal("0")
        variance = total_cost - standard_cost

        await self.run_repo.update(run, {
            "status": "closed",
            "variance_amount": variance,
        })

        from app.clients.webhook_client import emit_event
        await emit_event("production.run.closed", tenant_id, {
            "run_id": run.id, "run_number": run.run_number,
            "total_cost": float(total_cost), "variance": float(variance),
        })

        return await self.run_repo.get(tenant_id, run_id)

    # ── Emission/Receipt queries ─────────────────────────────────────────────

    async def list_emissions(self, tenant_id: str, run_id: str):
        return await self.emission_repo.list_by_run(tenant_id, run_id)

    async def get_emission(self, tenant_id: str, emission_id: str):
        e = await self.emission_repo.get(tenant_id, emission_id)
        if not e:
            raise NotFoundError("Emision no encontrada")
        return e

    async def list_receipts(self, tenant_id: str, run_id: str):
        return await self.receipt_repo.list_by_run(tenant_id, run_id)

    async def get_receipt(self, tenant_id: str, receipt_id: str):
        r = await self.receipt_repo.get(tenant_id, receipt_id)
        if not r:
            raise NotFoundError("Recibo no encontrado")
        return r

    # ── Resources CRUD ─────────────────────────────────────────────────────────

    async def list_resources(self, tenant_id: str):
        return await self.resource_repo.list(tenant_id)

    async def get_resource(self, tenant_id: str, resource_id: str):
        r = await self.resource_repo.get(tenant_id, resource_id)
        if not r:
            raise NotFoundError("Recurso no encontrado")
        return r

    async def create_resource(self, tenant_id: str, data: dict):
        return await self.resource_repo.create(tenant_id, data)

    async def update_resource(self, tenant_id: str, resource_id: str, data: dict):
        r = await self.resource_repo.get(tenant_id, resource_id)
        if not r:
            raise NotFoundError("Recurso no encontrado")
        return await self.resource_repo.update(r, {k: v for k, v in data.items() if v is not None})

    async def delete_resource(self, tenant_id: str, resource_id: str):
        r = await self.resource_repo.get(tenant_id, resource_id)
        if not r:
            raise NotFoundError("Recurso no encontrado")
        await self.resource_repo.soft_delete(r)

    # ── Capacity Check ───────────────────────────────────────────────────────

    async def check_capacity(self, tenant_id: str, run_id: str):
        """Check if resources have enough capacity for a production run."""
        run = await self._get_run_or_404(tenant_id, run_id)
        recipe = await self._get_recipe_or_404(tenant_id, run.recipe_id)
        multiplier = run.multiplier
        lines = []
        all_ok = True

        for res in (recipe.resources or []):
            resource = res.resource
            if not resource:
                continue
            required_hrs = (res.hours_per_unit * recipe.output_quantity * multiplier) + res.setup_time_hours
            # Effective daily capacity
            daily_cap = resource.capacity_hours_per_day * resource.shifts_per_day * (resource.efficiency_pct / Decimal("100"))
            if resource.available_hours_override:
                daily_cap = resource.available_hours_override
            # Days in planned window
            days = Decimal("1")
            if run.planned_start_date and run.planned_end_date:
                delta = (run.planned_end_date - run.planned_start_date).days
                days = max(Decimal(str(delta)), Decimal("1"))
            total_cap = daily_cap * days
            committed = await self.resource_repo.committed_hours(resource.id)
            available = total_cap - committed
            has_cap = available >= required_hrs
            if not has_cap:
                all_ok = False
            utilization = (committed + required_hrs) / total_cap * Decimal("100") if total_cap > 0 else Decimal("0")
            lines.append({
                "resource_id": resource.id,
                "resource_name": resource.name,
                "required_hours": required_hrs,
                "available_hours": available,
                "committed_hours": committed,
                "utilization_pct": min(utilization, Decimal("999")),
                "has_capacity": has_cap,
            })

        return {"lines": lines, "all_have_capacity": all_ok}

    # ── MRP (Material Requirements Planning) ─────────────────────────────────

    async def mrp_explode(self, tenant_id: str, data: dict):
        """Explode BOM recursively, check stock, return buy + make suggestions."""
        recipe = await self._get_recipe_or_404(tenant_id, data["recipe_id"])
        quantity = Decimal(str(data["quantity"]))
        warehouse_id = data["warehouse_id"]
        consider_reserved = data.get("consider_reserved", True)
        auto_create_po = data.get("auto_create_po", False)

        buy_lines: list[dict] = []
        make_lines: list[dict] = []
        total_estimated = Decimal("0")
        visited: set[str] = set()  # prevent circular references

        await self._mrp_recursive(
            tenant_id, recipe, quantity, warehouse_id, consider_reserved,
            buy_lines, make_lines, total_estimated, visited,
        )

        # Recalculate total
        total_estimated = sum(Decimal(str(l["required_qty"])) * Decimal(str(l["estimated_unit_cost"])) for l in buy_lines)
        # Add resource costs
        for res in (recipe.resources or []):
            resource = res.resource
            if resource:
                hrs = (res.hours_per_unit * quantity) + res.setup_time_hours
                total_estimated += hrs * resource.cost_per_hour

        result = {
            "recipe_id": recipe.id,
            "recipe_name": recipe.name,
            "output_quantity": quantity,
            "lines": buy_lines,
            "make_suggestions": make_lines,
            "total_estimated_cost": total_estimated,
            "purchase_orders_created": [],
        }

        # Auto-create draft POs for buy shortages
        if auto_create_po:
            from app.repositories.purchase_order_repo import PORepository
            po_repo = PORepository(self.db)
            by_supplier: dict[str, list] = {}
            for line in buy_lines:
                if Decimal(str(line["shortage"])) > 0 and line.get("preferred_supplier_id"):
                    sid = line["preferred_supplier_id"]
                    by_supplier.setdefault(sid, []).append(line)

            for sid, supplier_lines in by_supplier.items():
                po_number = await po_repo.next_po_number(tenant_id)
                po = await po_repo.create({
                    "tenant_id": tenant_id,
                    "po_number": po_number,
                    "supplier_id": sid,
                    "status": "draft",
                    "warehouse_id": warehouse_id,
                    "is_auto_generated": True,
                    "notes": f"Auto-generada por MRP para receta {recipe.name}",
                    "lines": [
                        {
                            "product_id": sl["component_entity_id"],
                            "qty_ordered": sl["suggested_order_qty"],
                            "unit_cost": sl["estimated_unit_cost"],
                        }
                        for sl in supplier_lines
                    ],
                })
                result["purchase_orders_created"].append(po.id)

        return result

    async def _mrp_recursive(
        self, tenant_id: str, recipe, quantity: Decimal, warehouse_id: str,
        consider_reserved: bool, buy_lines: list, make_lines: list,
        total_estimated: Decimal, visited: set,
    ):
        """Recursively explode BOM. Components with active recipes become 'make', others 'buy'."""
        if recipe.id in visited:
            return  # circular reference protection
        visited.add(recipe.id)

        multiplier = quantity / recipe.output_quantity if recipe.output_quantity > 0 else Decimal("1")

        for comp in (recipe.components or []):
            scrap_factor = Decimal("1") + (comp.scrap_percentage or Decimal("0")) / Decimal("100")
            required_qty = comp.quantity_required * multiplier * scrap_factor
            level = await self.stock_repo.get_level(comp.component_entity_id, warehouse_id)
            on_hand = level.qty_on_hand if level else Decimal("0")
            reserved = level.qty_reserved if level and consider_reserved else Decimal("0")
            available = on_hand - reserved
            shortage = max(Decimal("0"), required_qty - available)
            avg_cost = await self.layer_repo.weighted_avg_cost(comp.component_entity_id)

            entity = comp.component_entity
            supplier_id = None
            if entity and hasattr(entity, "preferred_supplier_id") and entity.preferred_supplier_id:
                supplier_id = entity.preferred_supplier_id

            # Check if this component has its own active recipe (sub-assembly)
            sub_recipe = await self._find_default_recipe(tenant_id, comp.component_entity_id)

            if sub_recipe and shortage > 0:
                # This is a "make" item — suggest producing it and recursively explode
                make_lines.append({
                    "component_entity_id": comp.component_entity_id,
                    "component_name": getattr(entity, "name", None) if entity else None,
                    "required_qty": required_qty,
                    "available_qty": available,
                    "shortage": shortage,
                    "suggested_order_qty": shortage,
                    "preferred_supplier_id": None,
                    "lead_time_offset_days": comp.lead_time_offset_days or 0,
                    "estimated_unit_cost": avg_cost,
                    "action": "make",
                    "sub_recipe_id": sub_recipe.id,
                    "sub_recipe_name": sub_recipe.name,
                })
                # Recursively explode the sub-assembly's BOM for the shortage quantity
                await self._mrp_recursive(
                    tenant_id, sub_recipe, shortage, warehouse_id,
                    consider_reserved, buy_lines, make_lines, total_estimated, visited,
                )
            else:
                # This is a "buy" item
                buy_lines.append({
                    "component_entity_id": comp.component_entity_id,
                    "component_name": getattr(entity, "name", None) if entity else None,
                    "required_qty": required_qty,
                    "available_qty": available,
                    "shortage": shortage,
                    "suggested_order_qty": shortage,
                    "preferred_supplier_id": supplier_id,
                    "lead_time_offset_days": comp.lead_time_offset_days or 0,
                    "estimated_unit_cost": avg_cost,
                    "action": "buy",
                    "sub_recipe_id": None,
                    "sub_recipe_name": None,
                })

    async def _find_default_recipe(self, tenant_id: str, entity_id: str):
        """Find the default active recipe for a product (sub-assembly detection)."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(EntityRecipe)
            .where(
                EntityRecipe.tenant_id == tenant_id,
                EntityRecipe.output_entity_id == entity_id,
                EntityRecipe.is_active.is_(True),
                EntityRecipe.bom_type == "production",
            )
            .order_by(EntityRecipe.is_default.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_run_or_404(self, tenant_id: str, run_id: str):
        run = await self.run_repo.get(tenant_id, run_id)
        if not run:
            raise NotFoundError("Orden de produccion no encontrada")
        return run

    async def _get_recipe_or_404(self, tenant_id: str, recipe_id: str):
        recipe = await self.recipe_repo.get(tenant_id, recipe_id)
        if not recipe:
            raise NotFoundError("Receta no encontrada")
        return recipe
