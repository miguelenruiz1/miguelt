"""Core stock business logic: receive, issue, transfer, adjust."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models import MovementType, Product, ProductType, StockLevel, StockMovement
from app.db.models.tracking import EntityBatch
from app.repositories.movement_repo import MovementRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.stock_repo import StockRepository
from app.repositories.warehouse_repo import WarehouseRepository
from app.services.costing_engine import CostingEngine


class StockService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.product_repo = ProductRepository(db)
        self.warehouse_repo = WarehouseRepository(db)
        self.stock_repo = StockRepository(db)
        self.movement_repo = MovementRepository(db)

    async def resolve_product_name(self, product_id: str, tenant_id: str) -> str | None:
        product = await self.product_repo.get_by_id(product_id, tenant_id)
        return product.name if product else None

    async def resolve_warehouse_name(self, warehouse_id: str, tenant_id: str) -> str | None:
        wh = await self.warehouse_repo.get_by_id(warehouse_id, tenant_id)
        return wh.name if wh else None

    async def _assert_product(self, product_id: str, tenant_id: str):
        p = await self.product_repo.get_by_id(product_id, tenant_id)
        if not p:
            raise NotFoundError(f"Product {product_id!r} not found")
        return p

    def _to_primary_qty(self, qty: Decimal, uom: str, product: Product) -> Decimal:
        """Convert quantity from the given UoM to the product's primary UoM.

        Secondary UoM / conversion factor fields have been removed from Product.
        Only primary UoM is supported; any other value raises an error.
        """
        if uom == "primary":
            return qty
        raise ValidationError(f"Unknown UoM '{uom}' for product {product.sku}. Only primary UoM is supported.")

    async def _get_product_type(self, product_id: str, tenant_id: str) -> ProductType | None:
        """Load the ProductType for a given product, if any."""
        result = await self.db.execute(
            select(ProductType)
            .join(Product, Product.product_type_id == ProductType.id)
            .where(Product.id == product_id, Product.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def _assert_warehouse(self, warehouse_id: str, tenant_id: str):
        wh = await self.warehouse_repo.get_by_id(warehouse_id, tenant_id)
        if not wh:
            raise NotFoundError(f"Warehouse {warehouse_id!r} not found")
        return wh

    async def _validate_location_capacity(self, location_id: str, product, quantity: Decimal, tenant_id: str) -> None:
        """Validate weight and unit capacity constraints on a warehouse location."""
        from app.db.models.warehouse import WarehouseLocation
        from sqlalchemy import select

        loc = (await self.db.execute(select(WarehouseLocation).where(WarehouseLocation.id == location_id))).scalar_one_or_none()
        if not loc:
            return

        if loc.blocked_inbound:
            raise ValidationError(f"Ubicacion '{loc.name}' bloqueada para entradas" + (f": {loc.block_reason}" if loc.block_reason else ""))

        # Weight check
        if loc.max_weight_kg and product.weight_per_unit:
            from app.db.models.stock import StockLevel
            from sqlalchemy import func
            current_weight_result = await self.db.execute(
                select(func.coalesce(func.sum(StockLevel.qty_on_hand * product.weight_per_unit), 0))
                .where(StockLevel.location_id == location_id, StockLevel.tenant_id == tenant_id)
            )
            current_weight = float(current_weight_result.scalar_one())
            new_weight = float(quantity) * float(product.weight_per_unit or 0)
            if current_weight + new_weight > float(loc.max_weight_kg):
                raise ValidationError(
                    f"Peso excede capacidad de ubicacion '{loc.name}': "
                    f"actual {current_weight:.1f}kg + nuevo {new_weight:.1f}kg = {current_weight + new_weight:.1f}kg > max {float(loc.max_weight_kg):.1f}kg"
                )

        # Unit capacity check
        if loc.max_capacity:
            from app.db.models.stock import StockLevel
            from sqlalchemy import func
            current_units_result = await self.db.execute(
                select(func.coalesce(func.sum(StockLevel.qty_on_hand), 0))
                .where(StockLevel.location_id == location_id, StockLevel.tenant_id == tenant_id)
            )
            current_units = float(current_units_result.scalar_one())
            if current_units + float(quantity) > loc.max_capacity:
                raise ValidationError(
                    f"Capacidad excedida en ubicacion '{loc.name}': "
                    f"actual {int(current_units)} + nuevo {int(quantity)} = {int(current_units + float(quantity))} > max {loc.max_capacity}"
                )

    async def receive(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        quantity: Decimal,
        unit_cost: Decimal | None = None,
        reference: str | None = None,
        notes: str | None = None,
        batch_number: str | None = None,
        performed_by: str | None = None,
        batch_id: str | None = None,
        variant_id: str | None = None,
        location_id: str | None = None,
        uom: str = "primary",
    ) -> StockMovement:
        product = await self._assert_product(product_id, tenant_id)
        await self._assert_warehouse(warehouse_id, tenant_id)
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        if unit_cost is None or unit_cost <= 0:
            raise ValidationError("El costo unitario es obligatorio y debe ser mayor a cero para ingresar mercancía al inventario")

        qty_primary = self._to_primary_qty(quantity, uom, product)

        level = await self.stock_repo.upsert_level(tenant_id, product_id, warehouse_id, qty_primary, batch_id, unit_cost=unit_cost, variant_id=variant_id, location_id=location_id)

        # Location assignment: explicit > product-type entry rule > None
        if level:
            pt = await self._get_product_type(product_id, tenant_id)
            if pt and pt.requires_qc:
                level.qc_status = "pending_qc"
            effective_location_id = location_id or (pt.entry_rule_location_id if pt else None)
            if effective_location_id:
                await self._validate_location_capacity(effective_location_id, product, qty_primary, tenant_id)
                level.location_id = effective_location_id
            await self.db.flush()

        movement = await self.movement_repo.create({
            "tenant_id": tenant_id,
            "movement_type": MovementType.purchase,
            "product_id": product_id,
            "to_warehouse_id": warehouse_id,
            "quantity": qty_primary,
            "original_qty": quantity if uom != "primary" else None,
            "uom": uom,
            "unit_cost": unit_cost,
            "reference": reference,
            "notes": notes,
            "batch_number": batch_number,
            "performed_by": performed_by,
            "variant_id": variant_id,
        })

        # Costing engine: create layer for incoming stock
        if unit_cost is not None and unit_cost > 0:
            engine = CostingEngine(self.db)
            await engine.on_stock_in(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=qty_primary,
                unit_cost=unit_cost,
                movement_id=movement.id,
                batch_id=batch_id,
            )

        return movement

    async def issue(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        quantity: Decimal,
        reference: str | None = None,
        notes: str | None = None,
        performed_by: str | None = None,
        batch_id: str | None = None,
        variant_id: str | None = None,
        uom: str = "primary",
    ) -> StockMovement:
        product = await self._assert_product(product_id, tenant_id)
        await self._assert_warehouse(warehouse_id, tenant_id)
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")

        qty_primary = self._to_primary_qty(quantity, uom, product)

        # Feature 1: QC blocking — reject issue if stock is in quarantine
        level = await self.stock_repo.get_level(product_id, warehouse_id, batch_id, variant_id)
        if level and getattr(level, "qc_status", "approved") == "pending_qc":
            raise ValidationError("Stock en cuarentena QC, no se puede despachar")

        # Feature 2: FEFO / LIFO dispatch rule
        pt = await self._get_product_type(product_id, tenant_id)
        dispatch_rule = pt.dispatch_rule if pt else "fifo"

        if batch_id is None and dispatch_rule in ("fefo", "lifo"):
            # Multi-batch dispatch — one movement per batch consumed
            allocations = await self._dispatch_multi_batch(
                tenant_id, product_id, warehouse_id, qty_primary, dispatch_rule, variant_id,
            )
            last_movement = None
            for alloc_batch_id, alloc_qty in allocations:
                last_movement = await self.movement_repo.create({
                    "tenant_id": tenant_id,
                    "movement_type": MovementType.sale,
                    "product_id": product_id,
                    "from_warehouse_id": warehouse_id,
                    "quantity": alloc_qty,
                    "uom": uom,
                    "reference": reference,
                    "notes": notes,
                    "performed_by": performed_by,
                    "variant_id": variant_id,
                    "batch_id": alloc_batch_id,
                })
            return last_movement  # type: ignore[return-value]
        else:
            available = level.qty_on_hand if level else Decimal("0")
            if available < qty_primary:
                raise ValidationError(
                    f"Insufficient stock: available {available}, requested {qty_primary}"
                )
            await self.stock_repo.upsert_level(tenant_id, product_id, warehouse_id, -qty_primary, batch_id, variant_id=variant_id)

            # Costing engine: calculate COGS
            engine = CostingEngine(self.db)
            valuation = product.valuation_method if product else "weighted_average"
            cost_total_val, layer_ids = await engine.on_stock_out(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=qty_primary,
                valuation_method=valuation or "weighted_average",
            )
            cost_unit = cost_total_val / qty_primary if qty_primary else Decimal("0")

            return await self.movement_repo.create({
                "tenant_id": tenant_id,
                "movement_type": MovementType.sale,
                "product_id": product_id,
                "from_warehouse_id": warehouse_id,
                "quantity": qty_primary,
                "original_qty": quantity if uom != "primary" else None,
                "uom": uom,
                "unit_cost": cost_unit,
                "cost_total": cost_total_val,
                "layer_consumed_ids": layer_ids,
                "reference": reference,
                "notes": notes,
                "performed_by": performed_by,
                "variant_id": variant_id,
                "batch_id": batch_id,
            })

    async def _dispatch_multi_batch(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        quantity: Decimal,
        dispatch_rule: str,
        variant_id: str | None,
    ) -> list[tuple[str | None, Decimal]]:
        """Consume stock across multiple batches using FEFO or LIFO ordering.

        Expired batches (expiration_date < today) are excluded from dispatch.

        Returns a list of (batch_id, qty_deducted) tuples — one per batch layer consumed.
        """
        today = date.today()

        q = (
            select(StockLevel)
            .where(
                StockLevel.tenant_id == tenant_id,
                StockLevel.product_id == product_id,
                StockLevel.warehouse_id == warehouse_id,
                StockLevel.qty_on_hand > 0,
                StockLevel.qc_status == "approved",
            )
        )
        if variant_id is not None:
            q = q.where(StockLevel.variant_id == variant_id)
        else:
            q = q.where(StockLevel.variant_id.is_(None))

        # Always join batches so we can filter expired ones
        q = q.outerjoin(EntityBatch, StockLevel.batch_id == EntityBatch.id)

        # Exclude expired batches (batch with expiration_date < today)
        q = q.where(
            or_(
                StockLevel.batch_id.is_(None),          # non-batch stock is always OK
                EntityBatch.expiration_date.is_(None),   # no expiry = OK
                EntityBatch.expiration_date >= today,     # not yet expired
            )
        )

        if dispatch_rule == "fefo":
            q = q.order_by(EntityBatch.expiration_date.asc().nulls_last(), StockLevel.updated_at.asc())
        elif dispatch_rule == "lifo":
            q = q.order_by(StockLevel.updated_at.desc())
        else:
            q = q.order_by(StockLevel.updated_at.asc())

        result = await self.db.execute(q)
        levels = list(result.scalars().all())

        total_available = sum(sl.qty_on_hand for sl in levels)
        if total_available < quantity:
            raise ValidationError(
                f"Insufficient non-expired stock: available {total_available}, requested {quantity}"
            )

        allocations: list[tuple[str | None, Decimal]] = []
        remaining = quantity
        for sl in levels:
            if remaining <= 0:
                break
            deduct = min(sl.qty_on_hand, remaining)
            await self.stock_repo.upsert_level(
                tenant_id, product_id, warehouse_id, -deduct,
                batch_id=sl.batch_id, variant_id=variant_id,
            )
            allocations.append((sl.batch_id, deduct))
            remaining -= deduct

        return allocations

    async def transfer(
        self,
        tenant_id: str,
        product_id: str,
        from_warehouse_id: str,
        to_warehouse_id: str,
        quantity: Decimal,
        notes: str | None = None,
        performed_by: str | None = None,
        batch_id: str | None = None,
        variant_id: str | None = None,
        uom: str = "primary",
        from_location_id: str | None = None,
        to_location_id: str | None = None,
    ) -> StockMovement:
        product = await self._assert_product(product_id, tenant_id)
        await self._assert_warehouse(from_warehouse_id, tenant_id)
        await self._assert_warehouse(to_warehouse_id, tenant_id)
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        if from_warehouse_id == to_warehouse_id:
            raise ValidationError("Source and destination warehouses must differ")

        qty_primary = self._to_primary_qty(quantity, uom, product)

        level = await self.stock_repo.get_level(product_id, from_warehouse_id, batch_id, variant_id)
        available = level.qty_on_hand if level else Decimal("0")
        if available < qty_primary:
            raise ValidationError(
                f"Insufficient stock in source warehouse: available {available}, requested {qty_primary}"
            )

        await self.stock_repo.upsert_level(tenant_id, product_id, from_warehouse_id, -qty_primary, batch_id, variant_id=variant_id, location_id=from_location_id)
        await self.stock_repo.upsert_level(tenant_id, product_id, to_warehouse_id, qty_primary, batch_id, variant_id=variant_id, location_id=to_location_id)

        movement_data: dict = {
            "tenant_id": tenant_id,
            "movement_type": MovementType.transfer,
            "product_id": product_id,
            "from_warehouse_id": from_warehouse_id,
            "to_warehouse_id": to_warehouse_id,
            "quantity": qty_primary,
            "original_qty": quantity if uom != "primary" else None,
            "uom": uom,
            "notes": notes,
            "performed_by": performed_by,
            "variant_id": variant_id,
        }
        if from_location_id:
            movement_data["from_location_id"] = from_location_id
        if to_location_id:
            movement_data["to_location_id"] = to_location_id

        return await self.movement_repo.create(movement_data)

    async def initiate_transfer(
        self,
        tenant_id: str,
        product_id: str,
        from_warehouse_id: str,
        to_warehouse_id: str,
        quantity: Decimal,
        notes: str | None = None,
        performed_by: str | None = None,
        batch_id: str | None = None,
        variant_id: str | None = None,
        uom: str = "primary",
    ) -> StockMovement:
        """Phase 1: decrement origin, increment qty_in_transit at destination."""
        product = await self._assert_product(product_id, tenant_id)
        await self._assert_warehouse(from_warehouse_id, tenant_id)
        await self._assert_warehouse(to_warehouse_id, tenant_id)
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        if from_warehouse_id == to_warehouse_id:
            raise ValidationError("Source and destination warehouses must differ")

        qty_primary = self._to_primary_qty(quantity, uom, product)

        level = await self.stock_repo.get_level(product_id, from_warehouse_id, batch_id, variant_id)
        available = level.qty_on_hand if level else Decimal("0")
        if available < qty_primary:
            raise ValidationError(
                f"Insufficient stock in source warehouse: available {available}, requested {qty_primary}"
            )

        # Decrement origin
        await self.stock_repo.upsert_level(tenant_id, product_id, from_warehouse_id, -qty_primary, batch_id, variant_id=variant_id)

        # Increment qty_in_transit at destination
        dest_level = await self.stock_repo.get_level(product_id, to_warehouse_id, batch_id, variant_id)
        if dest_level is None:
            dest_level = await self.stock_repo.upsert_level(tenant_id, product_id, to_warehouse_id, Decimal("0"), batch_id, variant_id=variant_id)
            if dest_level:
                dest_level.qty_in_transit = qty_primary
            else:
                # upsert_level returns None when delta=0 and no existing record — create one
                import uuid as _uuid
                dest_level = StockLevel(
                    id=str(_uuid.uuid4()),
                    tenant_id=tenant_id,
                    product_id=product_id,
                    warehouse_id=to_warehouse_id,
                    batch_id=batch_id,
                    variant_id=variant_id,
                    qty_on_hand=Decimal("0"),
                    qty_reserved=Decimal("0"),
                    qty_in_transit=qty_primary,
                )
                self.db.add(dest_level)
        else:
            dest_level.qty_in_transit += qty_primary
            dest_level.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        return await self.movement_repo.create({
            "tenant_id": tenant_id,
            "movement_type": MovementType.transfer,
            "product_id": product_id,
            "from_warehouse_id": from_warehouse_id,
            "to_warehouse_id": to_warehouse_id,
            "quantity": qty_primary,
            "original_qty": quantity if uom != "primary" else None,
            "uom": uom,
            "notes": notes,
            "performed_by": performed_by,
            "variant_id": variant_id,
            "status": "in_transit",
        })

    async def complete_transfer(
        self,
        tenant_id: str,
        movement_id: str,
    ) -> StockMovement:
        """Phase 2: move qty_in_transit → qty_on_hand at destination."""
        result = await self.db.execute(
            select(StockMovement).where(
                StockMovement.id == movement_id,
                StockMovement.tenant_id == tenant_id,
            )
        )
        movement = result.scalar_one_or_none()
        if not movement:
            raise NotFoundError(f"Movement {movement_id!r} not found")
        if movement.status != "in_transit":
            raise ValidationError(f"Movement is not in_transit (current: {movement.status})")
        if movement.movement_type != MovementType.transfer:
            raise ValidationError("Movement is not a transfer")

        # Move qty_in_transit → qty_on_hand at destination
        dest_level = await self.stock_repo.get_level(
            movement.product_id, movement.to_warehouse_id,
            variant_id=movement.variant_id,
        )
        if not dest_level:
            raise NotFoundError("Destination stock level not found")

        qty = movement.quantity
        dest_level.qty_in_transit = max(Decimal("0"), dest_level.qty_in_transit - qty)
        dest_level.qty_on_hand += qty
        dest_level.updated_at = datetime.now(timezone.utc)

        movement.status = "completed"
        movement.completed_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(movement)
        return movement

    async def adjust(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        new_qty: Decimal,
        reason: str | None = None,
        performed_by: str | None = None,
        batch_id: str | None = None,
        variant_id: str | None = None,
    ) -> StockMovement:
        await self._assert_product(product_id, tenant_id)
        await self._assert_warehouse(warehouse_id, tenant_id)
        if new_qty < 0:
            raise ValidationError("New quantity cannot be negative")

        level = await self.stock_repo.get_level(product_id, warehouse_id, batch_id, variant_id)
        current = level.qty_on_hand if level else Decimal("0")
        delta = new_qty - current
        movement_type = MovementType.adjustment_in if delta >= 0 else MovementType.adjustment_out

        await self.stock_repo.set_qty(tenant_id, product_id, warehouse_id, new_qty, batch_id, variant_id)

        # Costing engine: positive delta needs a layer at WAC so FIFO has
        # something to consume; negative delta consumes existing layers.
        if delta != 0:
            engine = CostingEngine(self.db)
            if delta > 0:
                wac = level.weighted_avg_cost if level and level.weighted_avg_cost else None
                if wac is None or Decimal(str(wac)) <= 0:
                    # Fallback: try product standard cost; otherwise skip layer
                    try:
                        prod = await self.product_repo.get_by_id(product_id, tenant_id)
                        wac = getattr(prod, "standard_cost", None) or getattr(prod, "average_cost", None)
                    except Exception:
                        wac = None
                if wac and Decimal(str(wac)) > 0:
                    await engine.on_stock_in(
                        tenant_id=tenant_id,
                        product_id=product_id,
                        warehouse_id=warehouse_id,
                        quantity=delta,
                        unit_cost=Decimal(str(wac)),
                    )
            else:
                try:
                    await engine.on_stock_out(
                        tenant_id=tenant_id,
                        product_id=product_id,
                        warehouse_id=warehouse_id,
                        quantity=abs(delta),
                    )
                except Exception:
                    pass

        return await self.movement_repo.create({
            "tenant_id": tenant_id,
            "movement_type": movement_type,
            "product_id": product_id,
            "to_warehouse_id": warehouse_id if delta >= 0 else None,
            "from_warehouse_id": warehouse_id if delta < 0 else None,
            "quantity": abs(delta),
            "notes": reason,
            "performed_by": performed_by,
            "variant_id": variant_id,
        })

    async def adjust_in(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        quantity: Decimal,
        reason: str | None = None,
        performed_by: str | None = None,
        variant_id: str | None = None,
        unit_cost: Decimal | None = None,
        uom: str = "primary",
    ) -> StockMovement:
        """Add quantity to stock (Ajuste +)."""
        product = await self._assert_product(product_id, tenant_id)
        await self._assert_warehouse(warehouse_id, tenant_id)
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")

        qty_primary = self._to_primary_qty(quantity, uom, product)

        await self.stock_repo.upsert_level(tenant_id, product_id, warehouse_id, qty_primary, variant_id=variant_id, unit_cost=unit_cost)

        # Costing engine: create a FIFO layer for the adjustment-in so future
        # consumption can value it. Without this, ajuste(+) inflates qty_on_hand
        # without backing layered cost, causing under-reported COGS.
        if unit_cost is not None and unit_cost > 0:
            engine = CostingEngine(self.db)
            await engine.on_stock_in(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=qty_primary,
                unit_cost=unit_cost,
            )

        return await self.movement_repo.create({
            "tenant_id": tenant_id,
            "movement_type": MovementType.adjustment_in,
            "product_id": product_id,
            "to_warehouse_id": warehouse_id,
            "quantity": qty_primary,
            "original_qty": quantity if uom != "primary" else None,
            "uom": uom,
            "unit_cost": unit_cost,
            "notes": reason,
            "performed_by": performed_by,
            "variant_id": variant_id,
        })

    async def adjust_out(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        quantity: Decimal,
        reason: str | None = None,
        performed_by: str | None = None,
        variant_id: str | None = None,
        uom: str = "primary",
    ) -> StockMovement:
        """Remove quantity from stock (Ajuste -)."""
        product = await self._assert_product(product_id, tenant_id)
        await self._assert_warehouse(warehouse_id, tenant_id)
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")

        qty_primary = self._to_primary_qty(quantity, uom, product)

        level = await self.stock_repo.get_level(product_id, warehouse_id, variant_id=variant_id)
        available = level.qty_on_hand if level else Decimal("0")
        if available < qty_primary:
            raise ValidationError(
                f"Stock insuficiente: disponible {available}, solicitado {qty_primary}"
            )

        await self.stock_repo.upsert_level(tenant_id, product_id, warehouse_id, -qty_primary, variant_id=variant_id)

        movement = await self.movement_repo.create({
            "tenant_id": tenant_id,
            "movement_type": MovementType.adjustment_out,
            "product_id": product_id,
            "from_warehouse_id": warehouse_id,
            "quantity": qty_primary,
            "original_qty": quantity if uom != "primary" else None,
            "uom": uom,
            "notes": reason,
            "performed_by": performed_by,
            "variant_id": variant_id,
        })

        await self._try_reorder(product_id, tenant_id, warehouse_id)
        return movement

    async def return_stock(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        quantity: Decimal,
        reference: str | None = None,
        notes: str | None = None,
        performed_by: str | None = None,
        variant_id: str | None = None,
        unit_cost: Decimal | None = None,
        uom: str = "primary",
    ) -> StockMovement:
        product = await self._assert_product(product_id, tenant_id)
        await self._assert_warehouse(warehouse_id, tenant_id)
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")

        qty_primary = self._to_primary_qty(quantity, uom, product)

        # Default to current WAC if no unit_cost provided (prevents cost distortion)
        effective_cost = unit_cost
        if effective_cost is None:
            level = await self.stock_repo.get_level(product_id, warehouse_id, variant_id=variant_id)
            if level and level.weighted_avg_cost:
                effective_cost = level.weighted_avg_cost

        await self.stock_repo.upsert_level(tenant_id, product_id, warehouse_id, qty_primary, variant_id=variant_id, unit_cost=effective_cost)

        # Costing engine: returns put stock back; create a layer at the
        # effective cost so subsequent FIFO consumption is valued correctly.
        if effective_cost is not None and Decimal(str(effective_cost)) > 0:
            engine = CostingEngine(self.db)
            await engine.on_stock_in(
                tenant_id=tenant_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=qty_primary,
                unit_cost=effective_cost,
            )

        return await self.movement_repo.create({
            "tenant_id": tenant_id,
            "movement_type": MovementType.return_,
            "product_id": product_id,
            "to_warehouse_id": warehouse_id,
            "quantity": qty_primary,
            "original_qty": quantity if uom != "primary" else None,
            "uom": uom,
            "unit_cost": effective_cost,
            "reference": reference,
            "notes": notes,
            "performed_by": performed_by,
            "variant_id": variant_id,
        })

    async def waste(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        quantity: Decimal,
        reason: str | None = None,
        performed_by: str | None = None,
        variant_id: str | None = None,
    ) -> StockMovement:
        await self._assert_product(product_id, tenant_id)
        await self._assert_warehouse(warehouse_id, tenant_id)
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")

        level = await self.stock_repo.get_level(product_id, warehouse_id, variant_id=variant_id)
        available = level.qty_on_hand if level else Decimal("0")
        if available < quantity:
            raise ValidationError(
                f"Insufficient stock: available {available}, requested {quantity}"
            )

        await self.stock_repo.upsert_level(tenant_id, product_id, warehouse_id, -quantity, variant_id=variant_id)

        movement = await self.movement_repo.create({
            "tenant_id": tenant_id,
            "movement_type": MovementType.waste,
            "product_id": product_id,
            "from_warehouse_id": warehouse_id,
            "quantity": quantity,
            "notes": reason,
            "performed_by": performed_by,
            "variant_id": variant_id,
        })

        await self._try_reorder(product_id, tenant_id, warehouse_id)
        return movement

    async def qc_approve(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        batch_id: str | None = None,
        variant_id: str | None = None,
    ) -> StockLevel:
        """Set QC status to 'approved' on a stock level."""
        level = await self.stock_repo.get_level_with_relations(product_id, warehouse_id, batch_id, variant_id)
        if not level:
            raise NotFoundError("Stock level not found")
        level.qc_status = "approved"
        level.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(level)
        return level

    async def qc_reject(
        self,
        tenant_id: str,
        product_id: str,
        warehouse_id: str,
        batch_id: str | None = None,
        variant_id: str | None = None,
        notes: str | None = None,
    ) -> StockLevel:
        """Set QC status to 'rejected' on a stock level."""
        level = await self.stock_repo.get_level_with_relations(product_id, warehouse_id, batch_id, variant_id)
        if not level:
            raise NotFoundError("Stock level not found")
        level.qc_status = "rejected"
        level.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(level)
        return level

    async def _try_reorder(self, product_id: str, tenant_id: str, warehouse_id: str | None = None):
        """Fire-and-forget: check if product needs auto-reorder after stock decrease."""
        import logging
        log = logging.getLogger("inventory.reorder")
        try:
            from app.services.reorder_service import ReorderService
            svc = ReorderService(self.db)
            await svc.check_and_trigger_reorder(product_id, tenant_id, warehouse_id)
        except Exception:
            log.exception("reorder_check_failed product=%s", product_id)

    async def get_summary(self, tenant_id: str) -> dict:
        from sqlalchemy import func, select
        from app.db.models import Product, StockLevel

        # Total SKUs
        result = await self.db.execute(
            select(func.count()).where(
                Product.tenant_id == tenant_id,
                Product.is_active == True,  # noqa: E712
            )
        )
        total_skus = result.scalar_one()

        # Low stock and out of stock
        low_stock_levels = await self.stock_repo.list_low_stock(tenant_id)
        low_stock_count = len(low_stock_levels)

        # Out of stock = active products with min_stock_level > 0 that have
        # NO stock level record in any warehouse (qty=0 deletes the record)
        products_with_stock = (
            select(StockLevel.product_id)
            .where(StockLevel.tenant_id == tenant_id)
            .distinct()
            .correlate(None)
        )
        result2 = await self.db.execute(
            select(func.count()).where(
                Product.tenant_id == tenant_id,
                Product.is_active == True,  # noqa: E712
                # Only count products that have stock tracking configured
                (Product.min_stock_level > 0) | (Product.reorder_point > 0),
                ~Product.id.in_(products_with_stock),
            )
        )
        out_of_stock_count = result2.scalar_one()

        # Total inventory value (qty_on_hand * weighted_avg_cost)
        result3 = await self.db.execute(
            select(func.coalesce(
                func.sum(StockLevel.qty_on_hand * func.coalesce(StockLevel.weighted_avg_cost, 0)),
                0
            ))
            .where(
                StockLevel.tenant_id == tenant_id,
            )
        )
        total_value = float(result3.scalar_one())

        return {
            "total_skus": total_skus,
            "total_value": total_value,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
        }
