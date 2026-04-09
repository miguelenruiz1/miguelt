"""Business logic for sales orders — draft → confirm → pick → ship → deliver.

Stock reservation flow:
  - confirm(): reserves stock (qty_reserved += qty) + creates StockReservation records
  - ship(): sets qty_shipped, persists shipping info — NO stock changes
  - deliver(): deducts physical stock (qty_on_hand -= qty_shipped),
               releases reservation (qty_reserved -= qty), creates sale movements,
               consumes StockReservation records
  - cancel(): releases reservation if order was confirmed/picking
  - return_order(): restocks shipped quantities (qty_on_hand += qty_shipped)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

# Colombia timezone (UTC-5) for DIAN fiscal date stamping
COL_TZ = timezone(timedelta(hours=-5))


def _co_date(dt: datetime | None) -> str | None:
    """Format a datetime as YYYY-MM-DD in Colombia timezone.

    Critical for DIAN: confirming at 19:30 Bogotá = 00:30 UTC next day, so
    without this conversion the invoice gets sent with tomorrow's date.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(COL_TZ).strftime("%Y-%m-%d")

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models import SalesOrderStatus, MovementType
from app.db.models.sales_order import SalesOrder
from app.repositories.batch_repo import BatchRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.movement_repo import MovementRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.sales_order_repo import SalesOrderRepository
from app.repositories.stock_repo import StockRepository
from app.repositories.warehouse_repo import WarehouseRepository
from app.services.stock_service import StockService

VALID_TRANSITIONS: dict[SalesOrderStatus, list[SalesOrderStatus]] = {
    SalesOrderStatus.draft:            [SalesOrderStatus.confirmed, SalesOrderStatus.pending_approval, SalesOrderStatus.canceled],
    SalesOrderStatus.pending_approval: [SalesOrderStatus.confirmed, SalesOrderStatus.rejected, SalesOrderStatus.canceled],
    SalesOrderStatus.confirmed:        [SalesOrderStatus.picking, SalesOrderStatus.canceled],
    SalesOrderStatus.picking:          [SalesOrderStatus.shipped, SalesOrderStatus.canceled],
    SalesOrderStatus.shipped:          [SalesOrderStatus.delivered, SalesOrderStatus.returned],
    SalesOrderStatus.delivered:        [SalesOrderStatus.returned],
    SalesOrderStatus.returned:         [],
    SalesOrderStatus.canceled:         [],
    SalesOrderStatus.rejected:         [SalesOrderStatus.pending_approval, SalesOrderStatus.canceled],
}

# States where stock is reserved (release on cancel)
_RESERVED_STATES = {SalesOrderStatus.confirmed, SalesOrderStatus.picking, SalesOrderStatus.shipped}


def recalculate_so_totals(so) -> None:
    """Recalculate all amounts on the SO from its lines. Modifies in-place.

    Multi-stack aware: if a line has any rows in its `line_taxes` collection,
    those override the legacy single tax_rate/retention_pct path. Each line_tax
    references a tax_rate whose `category.behavior` ('addition' | 'withholding')
    determines whether it sums into tax_amount or retention_amount, and whose
    `category.base_kind` ('subtotal' | 'subtotal_with_other_additions') controls
    cumulative bases (Brazil IPI on top of ICMS).

    Order of application for the legacy path:
      1. Per-line: discount_amount = unit_price * qty * discount_pct / 100
      2. Per-line: line_subtotal = unit_price * qty - discount_amount
      3. Per-line: line_total = line_subtotal * (1 - so_discount_pct/100) * (1 + tax_rate/100)
      4. SO: subtotal = sum(line_subtotal)
      5. SO: discount_amount = subtotal * discount_pct / 100
      6. SO: tax_amount = sum of per-line taxes
      7. SO: total = subtotal - discount_amount + tax_amount
    """
    D100 = Decimal("100")
    so_disc_pct = Decimal(str(so.discount_pct or 0))
    so_disc_factor = (D100 - so_disc_pct) / D100  # e.g. 0.95 for 5% discount

    subtotal = Decimal("0")
    tax_total = Decimal("0")

    for line in so.lines:
        qty = Decimal(str(line.qty_ordered))
        price = Decimal(str(line.unit_price))
        lpct = Decimal(str(line.discount_pct or 0))
        tax_rate = Decimal(str(line.tax_rate or 0))

        base = price * qty
        line.discount_amount = (base * lpct / D100).quantize(Decimal("0.0001"))
        line.line_subtotal = (base - line.discount_amount).quantize(Decimal("0.0001"))

        # Tax is on line_subtotal after applying the global discount proportionally
        taxable = line.line_subtotal * so_disc_factor
        line_tax = (taxable * tax_rate / D100).quantize(Decimal("0.0001"))

        # line_total = (line_subtotal * so_discount_factor) + line tax — INCLUDES
        # the global discount so the sum of line totals matches so.total exactly,
        # avoiding DIAN reject due to header/lines mismatch.
        line_taxable = line.line_subtotal * so_disc_factor
        line.line_total = (
            line_taxable + (line_taxable * tax_rate / D100)
        ).quantize(Decimal("0.01"))

        subtotal += line.line_subtotal
        tax_total += line_tax

    so.subtotal = subtotal.quantize(Decimal("0.01"))
    so.discount_amount = (subtotal * so_disc_pct / D100).quantize(Decimal("0.01"))
    so.tax_amount = tax_total.quantize(Decimal("0.01"))
    so.total = (subtotal - so.discount_amount + so.tax_amount).quantize(Decimal("0.01"))

    # ── Extended tax fields (retention, totals with tax) ───────────────────
    # If a line has any line_taxes (multi-stack), use those. Otherwise fall
    # back to the legacy single tax_rate_pct + retention_pct columns.
    total_retention = Decimal("0")
    total_addition_override = Decimal("0")
    any_multi_stack = False

    for line in so.lines:
        line_sub = Decimal(str(line.line_subtotal))
        line_taxes = list(getattr(line, "line_taxes", None) or [])

        if line_taxes:
            any_multi_stack = True
            line_addition = Decimal("0")
            line_withholding = Decimal("0")
            taxable_base = (line_sub * so_disc_factor).quantize(Decimal("0.0001"))

            # Pass 1: non-cumulative additions on the subtotal
            non_cumulative_total = Decimal("0")
            for lt in line_taxes:
                rate = getattr(lt, "rate", None)
                cat = getattr(rate, "category", None) if rate else None
                if cat is None or cat.behavior != "addition":
                    continue
                if cat.base_kind == "subtotal_with_other_additions":
                    continue
                rate_frac = Decimal(str(rate.rate))
                amount = (taxable_base * rate_frac).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                lt.rate_pct = rate_frac
                lt.base_amount = taxable_base
                lt.tax_amount = amount
                lt.behavior = "addition"
                line_addition += amount
                non_cumulative_total += amount

            # Pass 2: cumulative additions (Brazil IPI on top of ICMS)
            for lt in line_taxes:
                rate = getattr(lt, "rate", None)
                cat = getattr(rate, "category", None) if rate else None
                if cat is None or cat.behavior != "addition":
                    continue
                if cat.base_kind != "subtotal_with_other_additions":
                    continue
                rate_frac = Decimal(str(rate.rate))
                base = taxable_base + non_cumulative_total
                amount = (base * rate_frac).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                lt.rate_pct = rate_frac
                lt.base_amount = base
                lt.tax_amount = amount
                lt.behavior = "addition"
                line_addition += amount

            # Pass 3: withholdings (always on subtotal)
            for lt in line_taxes:
                rate = getattr(lt, "rate", None)
                cat = getattr(rate, "category", None) if rate else None
                if cat is None or cat.behavior != "withholding":
                    continue
                rate_frac = Decimal(str(rate.rate))
                amount = (taxable_base * rate_frac).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                lt.rate_pct = rate_frac
                lt.base_amount = taxable_base
                lt.tax_amount = amount
                lt.behavior = "withholding"
                line_withholding += amount

            line.tax_amount = line_addition
            line.retention_amount = line_withholding
            line.line_total_with_tax = (line_sub + line_addition).quantize(Decimal("0.0001"))
            total_addition_override += line_addition
            total_retention += line_withholding

        else:
            # Legacy single-tax path
            if getattr(line, "tax_rate_pct", None) is not None:
                tax_rate_frac = Decimal(str(line.tax_rate_pct))
            else:
                tax_rate_frac = Decimal(str(line.tax_rate or 0)) / D100
            retention_pct = Decimal(str(line.retention_pct)) if getattr(line, "retention_pct", None) else None

            line_tax = (line_sub * so_disc_factor * tax_rate_frac).quantize(Decimal("0.0001"))
            line.tax_amount = line_tax
            line.line_total_with_tax = (line_sub + (line_sub * tax_rate_frac)).quantize(Decimal("0.0001"))

            if retention_pct:
                ret = (line_sub * so_disc_factor * retention_pct).quantize(Decimal("0.0001"))
                line.retention_amount = ret
                total_retention += ret
            else:
                line.retention_amount = Decimal("0")

    if any_multi_stack:
        so.tax_amount = total_addition_override.quantize(Decimal("0.01"))
        so.total = (so.subtotal - so.discount_amount + so.tax_amount).quantize(Decimal("0.01"))
    so.total_retention = total_retention.quantize(Decimal("0.01"))
    so.total_with_tax = (so.subtotal - so.discount_amount + so.tax_amount).quantize(Decimal("0.01"))
    so.total_payable = (so.total_with_tax - so.total_retention).quantize(Decimal("0.01"))


class SalesOrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SalesOrderRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.product_repo = ProductRepository(db)
        self.warehouse_repo = WarehouseRepository(db)
        self.stock_repo = StockRepository(db)
        self.movement_repo = MovementRepository(db)
        self.batch_repo = BatchRepository(db)
        self.stock_service = StockService(db)

    async def list(self, tenant_id: str, **kwargs):
        return await self.repo.list(tenant_id, **kwargs)

    async def get(self, order_id: str, tenant_id: str):
        o = await self.repo.get_by_id(order_id, tenant_id)
        if not o:
            raise NotFoundError("Sales order not found")
        return o

    async def _load_products_for_order(self, order, tenant_id: str) -> dict:
        """Bulk-fetch all products referenced in an order's lines.

        Returns dict[product_id -> Product]. Use this in confirm/ship/deliver/
        cancel/return flows instead of calling product_repo.get_by_id per line
        (was an N+1 in every flow).
        """
        from sqlalchemy import select as _select
        from app.db.models import Product
        product_ids = list({line.product_id for line in order.lines})
        if not product_ids:
            return {}
        rows = await self.db.execute(
            _select(Product).where(
                Product.id.in_(product_ids),
                Product.tenant_id == tenant_id,
            )
        )
        return {p.id: p for p in rows.scalars().all()}

    async def create(self, tenant_id: str, data: dict, lines: list[dict], user_id: str | None = None):
        customer = await self.customer_repo.get_by_id(data["customer_id"], tenant_id)
        if not customer:
            raise NotFoundError("Customer not found")

        # If customer comes from business_partners, ensure a legacy customer record exists for FK
        from app.db.models.partner import BusinessPartner
        from app.db.models import Customer
        if isinstance(customer, BusinessPartner):
            existing_legacy = (await self.db.execute(
                select(Customer).where(Customer.id == customer.id, Customer.tenant_id == tenant_id)
            )).scalar_one_or_none()
            if not existing_legacy:
                legacy = Customer(
                    id=customer.id,
                    tenant_id=tenant_id,
                    name=customer.name,
                    code=customer.code,
                    contact_name=customer.contact_name,
                    email=customer.email,
                    phone=customer.phone,
                    tax_id=customer.tax_id,
                    is_active=True,
                )
                self.db.add(legacy)
                await self.db.flush()

        # Validate all lines have required financial fields
        if not lines:
            raise ValidationError("La orden de venta debe tener al menos una línea")
        for i, line in enumerate(lines):
            qty = line.get("qty_ordered")
            if qty is None or Decimal(str(qty)) <= 0:
                raise ValidationError(f"Línea {i+1}: la cantidad es obligatoria y debe ser mayor a cero")
            price = line.get("unit_price")
            if price is not None and Decimal(str(price)) < 0:
                raise ValidationError(f"Línea {i+1}: el precio unitario no puede ser negativo")

        order_number = await self.repo.next_number(tenant_id)

        from app.services.customer_price_service import CustomerPriceService
        from app.services.tax_service import TaxService
        cp_service = CustomerPriceService(self.db)
        tax_service = TaxService(self.db)

        processed_lines = []
        for line in lines:
            product = await self.product_repo.get_by_id(line["product_id"], tenant_id)
            if not product:
                raise NotFoundError(f"Product {line['product_id']!r} not found")
            qty = Decimal(str(line["qty_ordered"]))
            line_variant_id = line.get("variant_id")

            price_source: str | None = None
            customer_price_id: str | None = None
            original_unit_price: Decimal | None = None

            # Resolve the base price first (always needed for reference)
            base_price = Decimal(str(product.suggested_sale_price or 0))
            if line_variant_id:
                from app.repositories.variant_repo import ProductVariantRepository
                variant_repo = ProductVariantRepository(self.db)
                variant = await variant_repo.get_by_id(line_variant_id, tenant_id)
                if variant and variant.sale_price and Decimal(str(variant.sale_price)) > 0:
                    base_price = Decimal(str(variant.sale_price))

            # Price resolution: explicit > customer special > variant.sale_price > product.suggested_sale_price
            if line.get("unit_price") and Decimal(str(line["unit_price"])) > 0:
                unit_price = Decimal(str(line["unit_price"]))
                price_source = "manual"
                original_unit_price = base_price
            else:
                # 1. Check customer special price first
                cp = await cp_service.get_customer_price(
                    tenant_id, data["customer_id"], product.id, qty, variant_id=line_variant_id,
                )
                if cp:
                    unit_price = cp.price
                    price_source = "customer_special"
                    customer_price_id = cp.id
                    original_unit_price = base_price
                else:
                    # 2. Fall back to variant / product base price
                    unit_price = base_price
                    price_source = "product_base"

            discount_pct = Decimal(str(line.get("discount_pct", 0)))
            tax_rate = Decimal(str(line.get("tax_rate", "0")))

            # Resolve product tax rate
            product_tax_rate, product_tax_rate_id = await tax_service.get_product_tax_rate(
                product, tenant_id,
            )
            # Use explicit tax_rate from line if provided (>0), else use product's
            effective_tax_rate = tax_rate if tax_rate > 0 else (product_tax_rate * 100)
            effective_tax_rate_pct = product_tax_rate  # decimal form (0.19)
            effective_tax_rate_id = product_tax_rate_id
            retention_rate = getattr(product, "retention_rate", None)

            processed_lines.append({
                "product_id": line["product_id"],
                "variant_id": line_variant_id,
                "warehouse_id": line.get("warehouse_id"),
                "qty_ordered": qty,
                "unit_price": unit_price,
                "original_unit_price": original_unit_price,
                "discount_pct": discount_pct,
                "tax_rate": effective_tax_rate,
                "tax_rate_id": effective_tax_rate_id,
                "tax_rate_pct": effective_tax_rate_pct,
                "retention_pct": retention_rate,
                "notes": line.get("notes"),
                "price_source": price_source,
                "customer_price_id": customer_price_id,
                # Multi-stack tax rates (passed through to repo for line_taxes creation)
                "_tax_rate_ids": line.get("tax_rate_ids") or [],
            })

        so_discount_pct = Decimal(str(data.get("discount_pct", 0)))
        # Resolve warehouse_id: explicit → tenant default → null
        order_warehouse_id = data.get("warehouse_id")
        if not order_warehouse_id:
            default_wh = await self.warehouse_repo.get_default(tenant_id)
            if default_wh is not None:
                order_warehouse_id = default_wh.id
        order_data = {
            "tenant_id": tenant_id,
            "order_number": order_number,
            "customer_id": data["customer_id"],
            "warehouse_id": order_warehouse_id,
            "shipping_address": data.get("shipping_address"),
            "expected_date": data.get("expected_date"),
            "discount_pct": so_discount_pct,
            "discount_reason": data.get("discount_reason"),
            "currency": data.get("currency", "COP"),
            "notes": data.get("notes"),
            "created_by": user_id,
            # Placeholder totals — recalculated by repo.create_with_recalc
            "subtotal": Decimal("0"),
            "tax_amount": Decimal("0"),
            "discount_amount": Decimal("0"),
            "total": Decimal("0"),
        }
        return await self.repo.create(order_data, processed_lines)

    def _effective_warehouse(self, line, order) -> str | None:
        """Resolve effective warehouse: line-level override → SO-level default."""
        return line.warehouse_id or order.warehouse_id

    async def _resolve_wh_name(self, warehouse_id: str, tenant_id: str) -> str:
        wh = await self.warehouse_repo.get_by_id(warehouse_id, tenant_id)
        return wh.name if wh else warehouse_id[:8]

    async def confirm(self, order_id: str, tenant_id: str, user_id: str | None = None, user_name: str | None = None):
        """draft → confirmed (or pending_approval if threshold exceeded).

        Returns dict: { "order": SalesOrder, "backorder": SalesOrder|None, "split_preview": {...}, "approval_required": bool }

        Takes a SELECT FOR UPDATE on the SO row so two concurrent confirms can't
        both pass the status check and double-reserve stock.
        """
        from app.services.backorder_service import BackorderService
        from app.services.approval_service import ApprovalService
        from sqlalchemy import select as _select
        from app.db.models import SalesOrder

        # Lock the SO row first
        locked = await self.db.execute(
            _select(SalesOrder)
            .where(SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id)
            .with_for_update()
        )
        if locked.scalar_one_or_none() is None:
            raise NotFoundError(f"Sales order {order_id!r} not found")

        order = await self.get(order_id, tenant_id)

        # Only drafts can go through confirm flow
        if order.status != SalesOrderStatus.draft:
            self._assert_transition(order, SalesOrderStatus.confirmed)

        # Check if approval is needed
        approval_svc = ApprovalService(self.db)
        needs_approval = await approval_svc.requires_approval(order.total, tenant_id)

        if needs_approval:
            await approval_svc.request_approval(order, user_id or "", user_name)
            result = await self.get(order_id, tenant_id)
            return {
                "order": result,
                "backorder": None,
                "split_preview": {"has_backorder": False, "lines": []},
                "approval_required": True,
            }

        # No approval needed — proceed with normal confirmation
        return await self._do_confirm(order, order_id, tenant_id, user_id)

    async def _do_confirm(self, order, order_id: str, tenant_id: str, user_id: str | None = None):
        """Internal: execute actual confirmation (stock check, reserve, set status)."""
        from app.services.backorder_service import BackorderService

        self._assert_transition(order, SalesOrderStatus.confirmed)

        # Bulk pre-fetch products to avoid N+1 in the validation loop below
        product_map = await self._load_products_for_order(order, tenant_id)

        # Validate every line has a warehouse (line-level or SO-level)
        for line in order.lines:
            eff_wh = self._effective_warehouse(line, order)
            if not eff_wh:
                product = product_map.get(line.product_id)
                pname = product.name if product else line.product_id[:8]
                raise ValidationError(
                    f'No se puede confirmar: "{pname}" no tiene bodega asignada. '
                    f"Asigna una bodega a la orden o a cada línea antes de confirmar."
                )

        bo_svc = BackorderService(self.db)
        analysis = await bo_svc.analyze_and_split(order, tenant_id, user_id)

        total_confirmable = sum(cq for _, cq in analysis["confirmable_lines"])
        if total_confirmable == 0:
            raise ValidationError(
                "No se puede confirmar la orden: no hay stock disponible para ninguna línea. "
                "La orden permanece en borrador."
            )

        backorder = None
        if analysis["needs_backorder"]:
            backorder = await bo_svc.create_backorder(
                parent_order=order,
                backorder_lines=analysis["backorder_lines"],
                confirmable_lines=analysis["confirmable_lines"],
                tenant_id=tenant_id,
                user_id=user_id,
            )

        from app.services.reservation_service import ReservationService
        reservation_svc = ReservationService(self.db)
        try:
            await reservation_svc.reserve_for_so(order, tenant_id)
        except ValueError as exc:
            # If reservation fails and backorder was created, clean it up
            if backorder:
                await self.db.delete(backorder)
                for bl in backorder.lines:
                    await self.db.delete(bl)
                await self.db.flush()
                backorder = None
            raise ValidationError(str(exc))

        order.confirmed_at = datetime.now(timezone.utc)
        order.updated_by = user_id
        result = await self.repo.set_status(order, SalesOrderStatus.confirmed)

        await self._check_reorder_for_lines(order, tenant_id)

        if not result.cufe:
            await self._try_einvoice(result, tenant_id)
            result = await self.get(order_id, tenant_id)

        return {
            "order": result,
            "backorder": backorder,
            "split_preview": {
                "has_backorder": analysis["needs_backorder"],
                "lines": analysis["preview"],
            },
            "approval_required": False,
        }

    async def approve_and_confirm(self, order_id: str, tenant_id: str, approved_by: str, approved_by_name: str | None = None):
        """pending_approval → confirmed: approve then run the full confirm logic."""
        from app.services.approval_service import ApprovalService

        order = await self.get(order_id, tenant_id)
        approval_svc = ApprovalService(self.db)
        await approval_svc.approve(order, approved_by, approved_by_name)

        # Now run the actual confirm logic
        return await self._do_confirm(order, order_id, tenant_id, approved_by)

    async def start_picking(self, order_id: str, tenant_id: str, user_id: str | None = None):
        order = await self.get(order_id, tenant_id)
        self._assert_transition(order, SalesOrderStatus.picking)

        # Server-side stock validation before allowing picking
        check = await self.stock_check(order_id, tenant_id)
        if not check["ready_to_ship"]:
            insufficient = [ln for ln in check["lines"] if not ln["sufficient"]]
            msgs = [
                f"'{ln['product_name']}': disponible {ln['available']}, requerido {ln['required']}"
                for ln in insufficient[:5]
            ]
            raise ValidationError(
                "Stock insuficiente para iniciar picking. " + "; ".join(msgs)
            )

        order.updated_by = user_id
        return await self.repo.set_status(order, SalesOrderStatus.picking)

    async def ship(
        self, order_id: str, tenant_id: str,
        line_shipments: list[dict] | None = None,
        shipping_info: dict | None = None,
        user_id: str | None = None,
    ):
        """picking → shipped: sets qty_shipped and persists shipping info.

        Stock reservations remain active — physical deduction happens at deliver().
        """
        order = await self.get(order_id, tenant_id)
        self._assert_transition(order, SalesOrderStatus.shipped)

        # Persist shipping details into metadata JSONB
        if shipping_info:
            meta = dict(order.extra_data or {})
            meta["shipping_info"] = {k: v for k, v in shipping_info.items() if v}
            order.extra_data = meta
            addr_fields = {
                "address_line": shipping_info.get("address_line"),
                "city": shipping_info.get("city"),
                "state": shipping_info.get("state"),
                "zip_code": shipping_info.get("zip_code"),
                "country": shipping_info.get("country"),
            }
            if any(addr_fields.values()):
                order.shipping_address = {k: v for k, v in addr_fields.items() if v}

        # Resolve shipment quantities (no stock mutation)
        for line in order.lines:
            eff_wh = self._effective_warehouse(line, order)
            if not eff_wh:
                product = await self.product_repo.get_by_id(line.product_id, tenant_id)
                pname = product.name if product else line.product_id[:8]
                raise ValidationError(f'"{pname}" no tiene bodega asignada')

            qty = Decimal(str(line.qty_ordered))
            ship_uom = "primary"
            if line_shipments:
                match = next((s for s in line_shipments if s.get("line_id") == line.id), None)
                if match:
                    qty = Decimal(str(match["qty_shipped"]))
                    ship_uom = match.get("uom", "primary")

            # Convert to primary UoM if needed
            qty_primary = qty
            if ship_uom != "primary":
                raise ValidationError(f"Only primary UoM is supported for shipping. Received: {ship_uom}")

            # Validate stock availability before allowing shipment
            level = await self.stock_repo.get_level(
                line.product_id, eff_wh, variant_id=line.variant_id,
            )
            available = Decimal(str(level.qty_on_hand)) if level else Decimal("0")
            if available < qty_primary:
                product = await self.product_repo.get_by_id(line.product_id, tenant_id)
                pname = product.name if product else line.product_id[:8]
                raise ValidationError(
                    f"Stock insuficiente para '{pname}': "
                    f"disponible {available}, a despachar {qty_primary}"
                )

            line.qty_shipped = qty_primary

        # Auto-create backorder for any line shipped short of ordered. Without
        # this, the un-shipped quantity vanishes from the system: the SO closes
        # at "delivered" with less than ordered and the customer commitment is
        # silently dropped.
        backorder_pairs: list[tuple] = []
        confirmable_pairs: list[tuple] = []
        for line in order.lines:
            ordered = Decimal(str(line.qty_ordered or 0))
            shipped = Decimal(str(line.qty_shipped or 0))
            if shipped < ordered and shipped >= 0:
                missing = ordered - shipped
                backorder_pairs.append((line, missing))
                if shipped > 0:
                    confirmable_pairs.append((line, shipped))
        if backorder_pairs and not order.is_backorder:
            try:
                from app.services.backorder_service import BackorderService
                bo_svc = BackorderService(self.db)
                await bo_svc.create_backorder(
                    parent_order=order,
                    backorder_lines=backorder_pairs,
                    confirmable_lines=confirmable_pairs,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
            except Exception as exc:
                from app.core.logging import get_logger
                get_logger(__name__).warning(
                    "ship_backorder_create_failed",
                    order_id=order.id, error=str(exc),
                )

        order.updated_by = user_id

        # Generate remission number
        remission_number = await self.repo.next_remission_number(tenant_id)
        order.remission_number = remission_number
        order.remission_generated_at = datetime.now(timezone.utc)

        result = await self.repo.set_status(order, SalesOrderStatus.shipped)

        # Emit webhook event
        from app.clients.webhook_client import emit_event
        await emit_event("inventory.so.shipped", tenant_id, {
            "order_id": order.id, "order_number": order.order_number,
            "customer_id": order.customer_id, "total": float(order.total or 0),
        })

        return result

    async def deliver(self, order_id: str, tenant_id: str, user_id: str | None = None):
        """shipped → delivered: deducts physical stock, consumes reservations, creates sale movements.

        SELECT FOR UPDATE on the SO so concurrent deliver/cancel can't both
        consume the same reservations or double-deduct stock.
        """
        from sqlalchemy import select as _select
        from app.db.models import SalesOrder
        locked = await self.db.execute(
            _select(SalesOrder)
            .where(SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id)
            .with_for_update()
        )
        if locked.scalar_one_or_none() is None:
            raise NotFoundError(f"Sales order {order_id!r} not found")

        order = await self.get(order_id, tenant_id)
        # Guard against double-delivery (idempotency)
        if order.delivered_date is not None:
            raise ValidationError("Esta orden ya fue entregada.")
        self._assert_transition(order, SalesOrderStatus.delivered)

        # Bulk pre-fetch products to avoid N+1 in deliver loop
        product_map = await self._load_products_for_order(order, tenant_id)

        # Consume reservations (releases qty_reserved; stock deduction handled below)
        from app.services.reservation_service import ReservationService
        reservation_svc = ReservationService(self.db)
        has_reservations = await reservation_svc.consume_for_so(order, tenant_id)

        if has_reservations:
            # Deduct stock + create movements with COGS via stock_service.issue()
            for line in order.lines:
                eff_wh = self._effective_warehouse(line, order)
                if not eff_wh:
                    product = product_map.get(line.product_id)
                    pname = product.name if product else line.product_id[:8]
                    raise ValidationError(
                        f'No se puede entregar: "{pname}" no tiene bodega asignada.'
                    )
                qty_shipped = Decimal(str(line.qty_shipped))
                if qty_shipped <= 0:
                    continue

                line_variant_id = line.variant_id

                # Pre-validate: ensure sufficient physical stock before deducting
                level = await self.stock_repo.get_level(
                    line.product_id, eff_wh, variant_id=line_variant_id,
                )
                available = Decimal(str(level.qty_on_hand)) if level else Decimal("0")
                if available < qty_shipped:
                    product = await self.product_repo.get_by_id(line.product_id, tenant_id)
                    pname = product.name if product else line.product_id[:8]
                    raise ValidationError(
                        f"Stock insuficiente para '{pname}': "
                        f"disponible {available}, requerido {qty_shipped}. "
                        f"No se puede completar la entrega."
                    )

                # Use stock_service.issue() which handles:
                # - QC check, FEFO/LIFO dispatch, CostingEngine COGS, batch allocation
                try:
                    movement = await self.stock_service.issue(
                        tenant_id=tenant_id,
                        product_id=line.product_id,
                        warehouse_id=eff_wh,
                        quantity=qty_shipped,
                        reference=f"SO:{order.order_number}",
                        performed_by=user_id,
                        variant_id=line_variant_id,
                    )
                    if movement and movement.batch_id:
                        line.batch_id = movement.batch_id
                except ValidationError:
                    raise  # Re-raise stock validation errors — never swallow these
                except Exception:
                    # Fallback: simple deduction without costing (only for costing/batch errors)
                    await self.stock_repo.upsert_level(
                        tenant_id, line.product_id, eff_wh, -qty_shipped,
                        variant_id=line_variant_id,
                    )
                    await self.movement_repo.create({
                        "tenant_id": tenant_id,
                        "movement_type": MovementType.sale,
                        "product_id": line.product_id,
                        "from_warehouse_id": eff_wh,
                        "quantity": qty_shipped,
                        "reference": f"SO:{order.order_number}",
                        "performed_by": user_id,
                        "variant_id": line_variant_id,
                    })
        # else: old order without reservations — stock was already deducted at ship time

        order.updated_by = user_id
        result = await self.repo.set_status(order, SalesOrderStatus.delivered)

        from app.clients.webhook_client import emit_event
        await emit_event("inventory.so.delivered", tenant_id, {
            "order_id": order.id, "order_number": order.order_number,
            "customer_id": order.customer_id, "total": float(order.total or 0),
        })

        return result

    async def retry_einvoice(self, order_id: str, tenant_id: str):
        """Retry electronic invoicing for a failed order."""
        order = await self.get(order_id, tenant_id)
        allowed_statuses = {SalesOrderStatus.confirmed, SalesOrderStatus.picking, SalesOrderStatus.shipped, SalesOrderStatus.delivered}
        if order.status not in allowed_statuses:
            raise ValidationError("Solo se puede reintentar en órdenes confirmadas, en picking, enviadas o entregadas")
        if order.invoice_status not in (None, "failed"):
            raise ValidationError("Only failed or uninvoiced orders can be retried")
        if order.cufe:
            raise ValidationError("Order already has a CUFE — cannot retry")
        await self._try_einvoice(order, tenant_id)
        return await self.get(order_id, tenant_id)

    async def _try_einvoice(self, order, tenant_id: str):
        """Attempt to issue an electronic invoice via integration-service. Never raises.

        Priority: electronic-invoicing (MATIAS) → electronic-invoicing-sandbox → skip.
        """
        import logging
        log = logging.getLogger("inventory.einvoice")
        try:
            from app.api.deps import is_einvoicing_active

            provider_slug: str | None = None
            if await is_einvoicing_active(tenant_id):
                provider_slug = "matias"

            if not provider_slug:
                return

            order.invoice_status = "pending"
            await self.db.flush()

            # Build invoice payload from SO + customer
            customer = await self.customer_repo.get_by_id(order.customer_id, tenant_id)
            # Try to get richer data from BusinessPartner if available
            bp = None
            try:
                from app.db.models.partner import BusinessPartner
                from sqlalchemy import select as _sel
                bp_result = await self.db.execute(_sel(BusinessPartner).where(BusinessPartner.id == order.customer_id, BusinessPartner.tenant_id == tenant_id))
                bp = bp_result.scalar_one_or_none()
            except Exception:
                pass
            src = bp or customer  # prefer BusinessPartner (has fiscal fields)
            addr = getattr(src, "address", {}) or {}
            payment_terms = getattr(src, "payment_terms_days", 0) or 0
            # payment_form: 1=Contado, 2=Crédito
            payment_form = 2 if payment_terms > 0 else 1
            subtotal_after_discount = float(order.subtotal) - float(order.discount_amount)
            payload = {
                "number": order.order_number,
                "date": _co_date(order.confirmed_at),
                "currency": order.currency,
                "payment_form": getattr(order, "payment_form", None) or payment_form,
                "payment_method": getattr(order, "payment_method", 10),
                "payment_terms_days": payment_terms,
                "customer": {
                    "nit": getattr(src, "tax_id", "") or "222222222",
                    "dv": getattr(src, "dv", "") or "0",
                    "name": src.name if src else "",
                    "company_name": getattr(src, "company_name", "") or (src.name if src else ""),
                    "email": getattr(src, "email", "") or "",
                    "phone": getattr(src, "phone", "") or "",
                    "document_type": getattr(src, "document_type", "CC"),
                    "organization_type": getattr(src, "organization_type", 2),
                    "tax_regime": getattr(src, "tax_regime", 2),
                    "tax_liability": getattr(src, "tax_liability", 7),
                    "municipality_id": getattr(src, "municipality_id", 149),
                    "address": addr,
                    "address_line": addr.get("line1", ""),
                    "city": addr.get("city", ""),
                    "state": addr.get("state", ""),
                    "zip": addr.get("zip", ""),
                    "country": addr.get("country", "CO"),
                },
                "items": [],
                "global_discount_pct": float(order.discount_pct or 0),
                "global_discount_amount": float(order.discount_amount or 0),
                "subtotal": float(order.subtotal),
                "subtotal_after_discount": subtotal_after_discount,
                "tax_amount": float(order.tax_amount or 0),
                "total_retention": float(order.total_retention or 0),
                "total_payable": float(order.total_payable or order.total or 0),
                "total": float(order.total),
                "notes": order.notes or "",
            }
            # DIAN tax_id mapping by category slug.
            # Reference: DIAN Tipos de Tributo (anexo técnico facturación
            # electrónica). Most providers (MATIAS, Factura1, Factus, etc.)
            # follow these codes:
            #   01 = IVA
            #   02 = IC  (Impuesto al Consumo)  ← INC
            #   03 = ICA
            #   04 = INC (alias de IC en algunos catálogos)
            #   05 = ReteIVA
            #   06 = ReteRenta (Retefuente)
            #   07 = ReteICA
            DIAN_TAX_ID_BY_SLUG = {
                "iva":        1,
                "vat":        1,
                "impuesto":   1,  # generic addition fallback
                "ic":         2,
                "consumo":    2,
                "inc":        4,
                "ica":        3,
                "reteiva":    5,
                "retefuente": 6,
                "retencion":  6,
                "retention":  6,
                "irpf":       6,  # closest equivalent for export
                "withholding": 6,
                "reteica":    7,
            }
            DEFAULT_TAX_ID = 1  # if slug unknown, default to IVA

            for line in order.lines:
                product_name = getattr(line, "product_name", "") or (line.product.name if hasattr(line, "product") and line.product else "")
                line_taxes = list(getattr(line, "line_taxes", None) or [])

                # Build tax_totals (additions) and withholding_totals (withholdings)
                tax_totals_payload: list[dict] = []
                withholding_totals_payload: list[dict] = []
                for lt in line_taxes:
                    rate = getattr(lt, "rate", None)
                    cat = getattr(rate, "category", None) if rate else None
                    if not rate:
                        continue
                    slug = (cat.slug if cat else "iva").lower()
                    tax_id = DIAN_TAX_ID_BY_SLUG.get(slug, DEFAULT_TAX_ID)
                    entry = {
                        "tax_id": tax_id,
                        "percent": f"{float(lt.rate_pct) * 100:.2f}",  # rate_pct is fraction
                        "tax_amount": f"{float(lt.tax_amount):.2f}",
                        "taxable_amount": f"{float(lt.base_amount):.2f}",
                    }
                    behavior = (cat.behavior if cat else "addition")
                    if behavior == "withholding":
                        withholding_totals_payload.append(entry)
                    else:
                        tax_totals_payload.append(entry)

                # Legacy single-tax fallback (old SOs with no line_taxes)
                legacy_tax_rate = float(line.tax_rate or 0)
                legacy_retention_pct = float(line.retention_pct or 0) * 100 if line.retention_pct else 0

                payload["items"].append({
                    "description": product_name,
                    "sku": getattr(line, "product_sku", "") or (line.product.sku if hasattr(line, "product") and line.product else ""),
                    "product_name": product_name,
                    "quantity": float(line.qty_shipped if line.qty_shipped and line.qty_shipped > 0 else line.qty_ordered),
                    "unit_price": float(line.unit_price),
                    "discount_rate": float(line.discount_pct) / 100 if line.discount_pct else 0,
                    "discount_amount": float(line.discount_amount or 0),
                    # Legacy single-tax fields (kept for backwards compat)
                    "tax_rate": legacy_tax_rate,
                    "retention_pct": legacy_retention_pct,
                    "retention_amount": float(line.retention_amount or 0),
                    # Multi-stack: pre-built tax_totals/withholding_totals.
                    # MATIAS adapter prefers these if present.
                    "tax_totals": tax_totals_payload,
                    "withholding_totals": withholding_totals_payload,
                    "subtotal": float(line.line_subtotal or 0),
                    "total": float(line.line_total or 0),
                })

            # POST to integration-service (internal endpoint — no JWT needed)
            from app.api.deps import get_http_client
            from app.core.settings import get_settings
            settings = get_settings()
            http = get_http_client()
            resp = await http.post(
                f"{settings.INTEGRATION_SERVICE_URL}/api/v1/internal/invoices/{provider_slug}",
                json=payload,
                headers={"X-Tenant-Id": tenant_id},
                timeout=15.0,
            )

            if resp.status_code < 300:
                data = resp.json()
                order.cufe = data.get("cufe", "")
                order.invoice_number = data.get("invoice_number") or None
                order.invoice_pdf_url = data.get("pdf_url") or None
                order.invoice_remote_id = data.get("remote_id", "")
                order.invoice_provider = provider_slug
                order.invoice_status = data.get("status", "issued")
            else:
                order.invoice_status = "failed"
                order.invoice_provider = provider_slug
                log.warning("einvoice_failed order=%s provider=%s status=%s body=%s", order.id, provider_slug, resp.status_code, resp.text[:500])

            await self.db.flush()

        except Exception:
            log.exception("einvoice_error order=%s", getattr(order, "id", "?"))
            try:
                order.invoice_status = "failed"
                await self.db.flush()
            except Exception:
                pass

    async def _try_credit_note(self, order, tenant_id: str):
        """Attempt to issue a credit note via integration-service. Never raises."""
        import logging
        log = logging.getLogger("inventory.credit_note")
        try:
            from app.api.deps import is_einvoicing_active, is_einvoicing_sandbox_active

            provider_slug: str | None = None
            if await is_einvoicing_active(tenant_id):
                provider_slug = "matias"
            elif await is_einvoicing_sandbox_active(tenant_id):
                provider_slug = "sandbox"

            if not provider_slug:
                return

            order.credit_note_status = "pending"
            await self.db.flush()

            customer = await self.customer_repo.get_by_id(order.customer_id, tenant_id)
            payload = {
                "invoice_cufe": order.cufe,
                "invoice_number": order.invoice_number or order.order_number,
                "order_number": order.order_number,
                "date": _co_date(order.returned_at),
                "currency": order.currency,
                "reason": "Devolución de mercancía",
                "customer": {
                    "nit": getattr(customer, "tax_id", "") or "222222222",
                    "name": customer.name if customer else "",
                    "email": getattr(customer, "email", "") or "",
                },
                "items": [],
                "global_discount_pct": float(order.discount_pct or 0),
                "global_discount_amount": float(order.discount_amount or 0),
                "subtotal": float(order.subtotal),
                "subtotal_after_discount": float(order.subtotal) - float(order.discount_amount),
                "tax_amount": float(order.tax_amount or 0),
                "total": float(order.total),
            }
            for line in order.lines:
                product_name = getattr(line, "product_name", "") or (line.product.name if hasattr(line, "product") and line.product else "")
                payload["items"].append({
                    "description": product_name,
                    "sku": getattr(line, "product_sku", "") or (line.product.sku if hasattr(line, "product") and line.product else ""),
                    "product_name": product_name,
                    "quantity": float(line.qty_shipped if line.qty_shipped and line.qty_shipped > 0 else line.qty_ordered),
                    "unit_price": float(line.unit_price),
                    "discount_rate": float(line.discount_pct) / 100 if line.discount_pct else 0,
                    "discount_amount": float(line.discount_amount or 0),
                    "tax_rate": float(line.tax_rate),
                    "subtotal": float(line.line_subtotal or 0),
                    "total": float(line.line_total or 0),
                })

            from app.api.deps import get_http_client
            from app.core.settings import get_settings
            settings = get_settings()
            http = get_http_client()

            resp = await http.post(
                f"{settings.INTEGRATION_SERVICE_URL}/api/v1/internal/credit-notes/{provider_slug}",
                json=payload,
                headers={"X-Tenant-Id": tenant_id},
                timeout=15.0,
            )

            if resp.status_code < 300:
                data = resp.json()
                order.credit_note_cufe = data.get("cufe", "")
                order.credit_note_number = data.get("credit_note_number") or None
                order.credit_note_remote_id = data.get("remote_id", "")
                order.credit_note_status = data.get("status", "issued")
            else:
                order.credit_note_status = "failed"
                log.warning("credit_note_failed order=%s provider=%s status=%s body=%s", order.id, provider_slug, resp.status_code, resp.text[:500])

            await self.db.flush()

        except Exception:
            log.exception("credit_note_error order=%s", getattr(order, "id", "?"))
            try:
                order.credit_note_status = "failed"
                await self.db.flush()
            except Exception:
                pass

    async def retry_credit_note(self, order_id: str, tenant_id: str):
        """Retry credit note for a returned order that failed."""
        order = await self.get(order_id, tenant_id)
        if order.status != SalesOrderStatus.returned:
            raise ValidationError("Solo se puede reintentar en órdenes devueltas")
        if order.credit_note_status not in (None, "failed"):
            raise ValidationError("Only failed or un-issued credit notes can be retried")
        if order.credit_note_cufe:
            raise ValidationError("Order already has a credit note CUFE — cannot retry")
        if not order.cufe:
            raise ValidationError("Order has no invoice CUFE — cannot issue credit note")
        await self._try_credit_note(order, tenant_id)
        return await self.get(order_id, tenant_id)

    # ── Debit Note (DIAN — price adjustment) ────────────────────────────────

    async def issue_debit_note(self, order_id: str, tenant_id: str, reason: str, amount: float):
        """Issue a debit note for a price adjustment on an invoiced SO."""
        from decimal import Decimal as D
        order = await self.get(order_id, tenant_id)
        if not order.cufe:
            raise ValidationError("La orden no tiene factura — no se puede emitir nota debito")
        if order.debit_note_cufe:
            raise ValidationError("La orden ya tiene una nota debito emitida")

        order.debit_note_reason = reason
        order.debit_note_amount = D(str(amount))
        await self.db.flush()

        await self._try_debit_note(order, tenant_id, reason, amount)
        return await self.get(order_id, tenant_id)

    async def _try_debit_note(self, order, tenant_id: str, reason: str, amount: float):
        """Attempt to issue a debit note via integration-service. Never raises."""
        import logging
        log = logging.getLogger("inventory.debit_note")
        try:
            from app.api.deps import is_einvoicing_active, is_einvoicing_sandbox_active

            provider_slug: str | None = None
            if await is_einvoicing_active(tenant_id):
                provider_slug = "matias"
            elif await is_einvoicing_sandbox_active(tenant_id):
                provider_slug = "sandbox"

            if not provider_slug:
                return

            order.debit_note_status = "pending"
            await self.db.flush()

            customer = await self.customer_repo.get_by_id(order.customer_id, tenant_id)
            payload = {
                "type": "debit_note",
                "invoice_cufe": order.cufe,
                "invoice_number": order.invoice_number or order.order_number,
                "order_number": order.order_number,
                "date": _co_date(datetime.now(timezone.utc)),
                "currency": order.currency,
                "reason": reason,
                "adjustment_amount": amount,
                "customer": {
                    "nit": getattr(customer, "tax_id", "") or "222222222",
                    "name": customer.name if customer else "",
                    "email": getattr(customer, "email", "") or "",
                },
                "subtotal": amount,
                "tax_amount": 0,
                "total": amount,
            }

            from app.api.deps import get_http_client
            from app.core.settings import get_settings
            settings = get_settings()
            http = get_http_client()

            # Use credit-notes endpoint (DIAN treats debit notes similarly)
            resp = await http.post(
                f"{settings.INTEGRATION_SERVICE_URL}/api/v1/internal/credit-notes/{provider_slug}",
                json=payload,
                headers={"X-Tenant-Id": tenant_id},
                timeout=15.0,
            )

            if resp.status_code < 300:
                data = resp.json()
                order.debit_note_cufe = data.get("cufe", "")
                order.debit_note_number = data.get("credit_note_number") or None
                order.debit_note_remote_id = data.get("remote_id", "")
                order.debit_note_status = data.get("status", "issued")
            else:
                order.debit_note_status = "failed"
                log.warning("debit_note_failed order=%s status=%s", order.id, resp.status_code)

            await self.db.flush()

        except Exception:
            log.exception("debit_note_error order=%s", getattr(order, "id", "?"))
            try:
                order.debit_note_status = "failed"
                await self.db.flush()
            except Exception:
                pass

    async def retry_debit_note(self, order_id: str, tenant_id: str):
        """Retry a failed debit note."""
        order = await self.get(order_id, tenant_id)
        if not order.cufe:
            raise ValidationError("La orden no tiene factura")
        if order.debit_note_status not in (None, "failed"):
            raise ValidationError("Solo se puede reintentar notas debito fallidas")
        if order.debit_note_cufe:
            raise ValidationError("Ya existe una nota debito emitida")
        if not order.debit_note_reason or not order.debit_note_amount:
            raise ValidationError("Falta razon o monto de la nota debito")
        await self._try_debit_note(order, tenant_id, order.debit_note_reason, float(order.debit_note_amount))
        return await self.get(order_id, tenant_id)

    async def return_order(self, order_id: str, tenant_id: str, user_id: str | None = None):
        order = await self.get(order_id, tenant_id)
        self._assert_transition(order, SalesOrderStatus.returned)

        # Release any remaining active reservations (safety net)
        from app.services.reservation_service import ReservationService
        reservation_svc = ReservationService(self.db)
        await reservation_svc.release_for_so(order.id, tenant_id, "returned")

        for line in order.lines:
            eff_wh = self._effective_warehouse(line, order)
            if not eff_wh:
                product = await self.product_repo.get_by_id(line.product_id, tenant_id)
                pname = product.name if product else line.product_id[:8]
                raise ValidationError(
                    f'No se puede devolver: "{pname}" no tiene bodega asignada.'
                )
            qty = Decimal(str(line.qty_shipped))
            if qty > 0:
                line_variant_id = line.variant_id
                await self.stock_repo.upsert_level(tenant_id, line.product_id, eff_wh, qty, variant_id=line_variant_id)
                await self.movement_repo.create({
                    "tenant_id": tenant_id,
                    "movement_type": MovementType.return_,
                    "product_id": line.product_id,
                    "to_warehouse_id": eff_wh,
                    "quantity": qty,
                    "reference": f"SO-RET:{order.order_number}",
                    "performed_by": user_id,
                    "variant_id": line_variant_id,
                })

        order.returned_at = datetime.now(timezone.utc)
        order.updated_by = user_id
        result = await self.repo.set_status(order, SalesOrderStatus.returned)

        # Fire-and-forget credit note if the order has a CUFE (was invoiced)
        if order.cufe and not order.credit_note_cufe:
            await self._try_credit_note(order, tenant_id)
            # Re-fetch with eager loading to avoid MissingGreenlet on serialization
            result = await self.get(order_id, tenant_id)

        return result

    async def cancel(self, order_id: str, tenant_id: str, user_id: str | None = None):
        """Cancel order. If stock was reserved (confirmed/picking/shipped), release it.

        SELECT FOR UPDATE so cancel + deliver/ship don't race on reservations.
        """
        from sqlalchemy import select as _select
        from app.db.models import SalesOrder
        locked = await self.db.execute(
            _select(SalesOrder)
            .where(SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id)
            .with_for_update()
        )
        if locked.scalar_one_or_none() is None:
            raise NotFoundError(f"Sales order {order_id!r} not found")

        order = await self.get(order_id, tenant_id)
        self._assert_transition(order, SalesOrderStatus.canceled)

        # Release reservations via ReservationService
        if order.status in _RESERVED_STATES:
            from app.services.reservation_service import ReservationService
            reservation_svc = ReservationService(self.db)
            await reservation_svc.release_for_so(order.id, tenant_id, "canceled")

        order.updated_by = user_id
        return await self.repo.set_status(order, SalesOrderStatus.canceled)

    async def delete(self, order_id: str, tenant_id: str):
        order = await self.get(order_id, tenant_id)
        if order.status != SalesOrderStatus.draft:
            raise ValidationError("Only draft orders can be deleted")
        await self.repo.delete(order)

    async def count_by_status(self, tenant_id: str):
        return await self.repo.count_by_status(tenant_id)

    async def trace_backward(self, order_id: str, tenant_id: str):
        """Trace backward: SO -> which batches were used."""
        from sqlalchemy import select
        from app.db.models.tracking import EntityBatch
        from app.db.models.entity import Product
        from app.db.models.customer import Customer
        from app.db.models.stock import StockMovement
        from app.domain.schemas.tracking import SOBatchEntry, TraceBackwardOut

        order = await self.get(order_id, tenant_id)

        cust = (await self.db.execute(
            select(Customer.name).where(Customer.id == order.customer_id)
        )).scalar_one_or_none()

        batches_used: list[SOBatchEntry] = []

        for line in order.lines:
            if line.batch_id:
                batch = (await self.db.execute(
                    select(EntityBatch).where(EntityBatch.id == line.batch_id)
                )).scalar_one_or_none()
                prod = (await self.db.execute(
                    select(Product.name).where(Product.id == line.product_id)
                )).scalar_one_or_none()
                if batch:
                    batches_used.append(SOBatchEntry(
                        line_id=line.id,
                        product_id=line.product_id,
                        product_name=prod,
                        batch_id=batch.id,
                        batch_number=batch.batch_number,
                        expiration_date=batch.expiration_date,
                        qty_from_this_batch=float(line.qty_shipped),
                    ))

        so_ref = f"SO:{order.order_number}"
        mvs = (await self.db.execute(
            select(StockMovement).where(
                StockMovement.reference == so_ref,
                StockMovement.tenant_id == tenant_id,
                StockMovement.batch_id != None,  # noqa: E711
            )
        )).scalars().all()

        seen_batch_lines = {(e.line_id, e.batch_id) for e in batches_used}
        for m in mvs:
            matching_line = next(
                (l for l in order.lines if l.product_id == m.product_id),
                None,
            )
            line_id = matching_line.id if matching_line else ""
            key = (line_id, m.batch_id)
            if key in seen_batch_lines:
                continue
            seen_batch_lines.add(key)

            batch = (await self.db.execute(
                select(EntityBatch).where(EntityBatch.id == m.batch_id)
            )).scalar_one_or_none()
            prod = (await self.db.execute(
                select(Product.name).where(Product.id == m.product_id)
            )).scalar_one_or_none()
            if batch:
                batches_used.append(SOBatchEntry(
                    line_id=line_id,
                    product_id=m.product_id,
                    product_name=prod,
                    batch_id=batch.id,
                    batch_number=batch.batch_number,
                    expiration_date=batch.expiration_date,
                    qty_from_this_batch=float(m.quantity),
                ))

        return TraceBackwardOut(
            order_number=order.order_number,
            customer_id=order.customer_id,
            customer_name=cust,
            batches_used=batches_used,
        )

    async def stock_check(self, order_id: str, tenant_id: str) -> dict:
        """Verify stock availability per line in its effective warehouse.

        For confirmed orders: adds back this SO's own reservations to available,
        since the stock IS reserved for this order.
        """
        order = await self.get(order_id, tenant_id)

        # Get this SO's own reservations to exclude from "unavailable"
        from app.db.models.stock import StockReservation
        own_reservations: dict[tuple[str, str], Decimal] = {}
        if order.status in _RESERVED_STATES:
            result = await self.db.execute(
                select(
                    StockReservation.product_id,
                    StockReservation.warehouse_id,
                    func.sum(StockReservation.quantity),
                )
                .where(
                    StockReservation.sales_order_id == order.id,
                    StockReservation.status == "active",
                )
                .group_by(StockReservation.product_id, StockReservation.warehouse_id)
            )
            for row in result:
                own_reservations[(row[0], row[1])] = row[2]

        lines_result: list[dict] = []
        all_sufficient = True
        for line in order.lines:
            eff_wh = self._effective_warehouse(line, order)
            product = await self.product_repo.get_by_id(line.product_id, tenant_id)
            pname = product.name if product else line.product_id[:8]

            if not eff_wh:
                lines_result.append({
                    "line_id": line.id,
                    "product_name": pname,
                    "warehouse_name": "Sin bodega",
                    "required": float(line.qty_ordered),
                    "available": 0.0,
                    "sufficient": False,
                })
                all_sufficient = False
                continue

            wh_name = await self._resolve_wh_name(eff_wh, tenant_id)
            level = await self.stock_repo.get_level(line.product_id, eff_wh, variant_id=line.variant_id)
            raw_available = float(level.qty_on_hand - level.qty_reserved) if level else 0.0
            # Add back this SO's own reserved qty (it's already allocated for us)
            own_qty = float(own_reservations.get((line.product_id, eff_wh), Decimal("0")))
            available = raw_available + own_qty
            required = float(line.qty_ordered)
            sufficient = available >= required
            if not sufficient:
                all_sufficient = False
            lines_result.append({
                "line_id": line.id,
                "product_name": pname,
                "warehouse_name": wh_name,
                "required": required,
                "available": available,
                "sufficient": sufficient,
            })
        return {"ready_to_ship": all_sufficient, "lines": lines_result}

    async def update_line_warehouse(self, order_id: str, line_id: str, warehouse_id: str, tenant_id: str):
        """Update warehouse for a specific line. Only allowed on draft/confirmed orders."""
        order = await self.get(order_id, tenant_id)
        if order.status not in (SalesOrderStatus.draft, SalesOrderStatus.confirmed):
            raise ValidationError("Solo se puede cambiar la bodega en órdenes borrador o confirmadas")
        line = next((l for l in order.lines if l.id == line_id), None)
        if not line:
            raise NotFoundError("Línea no encontrada")
        # Validate warehouse exists
        wh = await self.warehouse_repo.get_by_id(warehouse_id, tenant_id)
        if not wh:
            raise NotFoundError("Bodega no encontrada")
        line.warehouse_id = warehouse_id
        await self.db.flush()
        return await self.get(order_id, tenant_id)

    async def apply_discount(
        self, order_id: str, tenant_id: str,
        discount_pct: float, discount_reason: str | None = None,
    ):
        """Apply or change the global discount on a draft SO."""
        order = await self.get(order_id, tenant_id)
        if order.status != SalesOrderStatus.draft:
            raise ValidationError("Solo se puede modificar el descuento en órdenes en borrador")
        if discount_pct < 0 or discount_pct > 100:
            raise ValidationError("El descuento debe estar entre 0% y 100%")
        order.discount_pct = Decimal(str(discount_pct))
        order.discount_reason = discount_reason
        recalculate_so_totals(order)
        await self.db.flush()
        return await self.get(order_id, tenant_id)

    async def list_backorders(self, order_id: str, tenant_id: str) -> list:
        """Return all backorder children for a given parent SO."""
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(SalesOrder)
            .where(SalesOrder.parent_so_id == order_id, SalesOrder.tenant_id == tenant_id)
            .options(selectinload(SalesOrder.lines))
            .order_by(SalesOrder.created_at)
        )
        return list(result.scalars().unique().all())

    async def confirm_backorder(self, order_id: str, tenant_id: str, user_id: str | None = None):
        """Confirm a backorder SO — same logic as confirm() but validates it IS a backorder."""
        order = await self.get(order_id, tenant_id)
        if not order.is_backorder:
            raise ValidationError("Esta orden no es un backorder")
        return await self.confirm(order_id, tenant_id, user_id)

    async def _check_reorder_for_lines(self, order, tenant_id: str):
        """Fire-and-forget: check if any product in this SO needs auto-reorder."""
        import logging
        log = logging.getLogger("inventory.reorder")
        try:
            from app.services.reorder_service import ReorderService
            reorder_svc = ReorderService(self.db)
            seen_products: set[str] = set()
            for line in order.lines:
                if line.product_id in seen_products:
                    continue
                seen_products.add(line.product_id)
                eff_wh = self._effective_warehouse(line, order)
                await reorder_svc.check_and_trigger_reorder(line.product_id, tenant_id, eff_wh)
        except Exception:
            log.exception("reorder_check_after_confirm order=%s", order.id)

    def _assert_transition(self, order, target: SalesOrderStatus):
        allowed = VALID_TRANSITIONS.get(order.status, [])
        if target not in allowed:
            raise ValidationError(
                f"Cannot transition from {order.status.value!r} to {target.value!r}"
            )
