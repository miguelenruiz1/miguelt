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

from datetime import datetime, timezone
from decimal import Decimal

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

    Order of application:
      1. Per-line: discount_amount = unit_price * qty * discount_pct / 100
      2. Per-line: line_subtotal = unit_price * qty - discount_amount
      3. Per-line: line_total = line_subtotal * (1 - so_discount_pct/100) * (1 + tax_rate/100)
         (but line_total stores pre-global-discount value for display: line_subtotal + line_tax)
      4. SO: subtotal = sum(line_subtotal)
      5. SO: discount_amount = subtotal * discount_pct / 100
      6. SO: tax_amount = sum of per-line taxes (on line_subtotal * (1 - so_discount_pct/100))
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

        # line_total = line_subtotal + line-level tax (before global discount, for display)
        line.line_total = (line.line_subtotal + (line.line_subtotal * tax_rate / D100)).quantize(Decimal("0.01"))

        subtotal += line.line_subtotal
        tax_total += line_tax

    so.subtotal = subtotal.quantize(Decimal("0.01"))
    so.discount_amount = (subtotal * so_disc_pct / D100).quantize(Decimal("0.01"))
    so.tax_amount = tax_total.quantize(Decimal("0.01"))
    so.total = (subtotal - so.discount_amount + so.tax_amount).quantize(Decimal("0.01"))

    # ── Extended tax fields (retention, totals with tax) ───────────────────
    total_retention = Decimal("0")
    for line in so.lines:
        line_sub = Decimal(str(line.line_subtotal))
        tax_rate_pct = Decimal(str(getattr(line, "tax_rate_pct", None) or line.tax_rate or 0))
        retention_pct = Decimal(str(line.retention_pct)) if getattr(line, "retention_pct", None) else None

        line_tax = (line_sub * so_disc_factor * tax_rate_pct / D100).quantize(Decimal("0.0001"))
        line.tax_amount = line_tax
        line.line_total_with_tax = (line_sub + (line_sub * tax_rate_pct / D100)).quantize(Decimal("0.0001"))

        if retention_pct:
            ret = (line_sub * so_disc_factor * retention_pct).quantize(Decimal("0.0001"))
            line.retention_amount = ret
            total_retention += ret
        else:
            line.retention_amount = Decimal("0")

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
            })

        so_discount_pct = Decimal(str(data.get("discount_pct", 0)))
        order_data = {
            "tenant_id": tenant_id,
            "order_number": order_number,
            "customer_id": data["customer_id"],
            "warehouse_id": data.get("warehouse_id"),
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
        """
        from app.services.backorder_service import BackorderService
        from app.services.approval_service import ApprovalService

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
        """shipped → delivered: deducts physical stock, consumes reservations, creates sale movements."""
        order = await self.get(order_id, tenant_id)
        self._assert_transition(order, SalesOrderStatus.delivered)

        # Consume reservations (releases qty_reserved; stock deduction handled below)
        from app.services.reservation_service import ReservationService
        reservation_svc = ReservationService(self.db)
        has_reservations = await reservation_svc.consume_for_so(order, tenant_id)

        if has_reservations:
            # Deduct stock + create movements with COGS via stock_service.issue()
            for line in order.lines:
                eff_wh = self._effective_warehouse(line, order)
                if not eff_wh:
                    continue
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
            subtotal_after_discount = float(order.subtotal) - float(order.discount_amount)
            payload = {
                "number": order.order_number,
                "date": order.confirmed_at.strftime("%Y-%m-%d") if order.confirmed_at else None,
                "currency": order.currency,
                "customer": {
                    "nit": getattr(customer, "tax_id", "") or "222222222",
                    "name": customer.name if customer else "",
                    "email": getattr(customer, "email", "") or "",
                },
                "items": [],
                "global_discount_pct": float(order.discount_pct or 0),
                "global_discount_amount": float(order.discount_amount or 0),
                "subtotal": float(order.subtotal),
                "subtotal_after_discount": subtotal_after_discount,
                "tax_amount": float(order.tax_amount or 0),
                "total": float(order.total),
                "notes": order.notes or "",
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
                "date": order.returned_at.strftime("%Y-%m-%d") if order.returned_at else None,
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
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
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
                continue
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
        """Cancel order. If stock was reserved (confirmed/picking/shipped), release it."""
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
