"""Sales order endpoints — full lifecycle."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.domain.schemas.sales_order import (
    ApprovalThresholdOut, ApprovalThresholdUpdate, ConfirmWithBackorderOut,
    LineWarehouseUpdate, PaginatedSOs, RejectRequest, ShipRequest,
    SOApprovalLogOut, SOCreate, SODiscountUpdate, SOLineOut, SOOut, SOUpdate,
    StockCheckResult, StockReservationOut,
)
from app.domain.schemas.tracking import TraceBackwardOut
from app.services.sales_order_service import SalesOrderService
from app.services.audit_service import InventoryAuditService

router = APIRouter(prefix="/api/v1/sales-orders", tags=["sales-orders"])

Viewer = Annotated[dict, Depends(require_permission("inventory.view"))]
Editor = Annotated[dict, Depends(require_permission("inventory.manage"))]
Approver = Annotated[dict, Depends(require_permission("so.approve"))]


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


@router.get("", response_model=PaginatedSOs)
async def list_sales_orders(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
    status: str | None = None,
    customer_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    svc = SalesOrderService(db)
    items, total = await svc.list(user["tenant_id"], status=status, customer_id=customer_id, offset=offset, limit=limit)
    return PaginatedSOs(items=items, total=total, offset=offset, limit=limit)


@router.get("/summary")
async def sales_summary(
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = SalesOrderService(db)
    return await svc.count_by_status(user["tenant_id"])


@router.get("/pending-approval", response_model=PaginatedSOs)
async def list_pending_approvals(
    _module: ModuleUser,
    user: Approver,
    db: AsyncSession = Depends(get_db_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List all SOs pending approval for the tenant."""
    svc = SalesOrderService(db)
    items, total = await svc.list(user["tenant_id"], status="pending_approval", offset=offset, limit=limit)
    return PaginatedSOs(items=items, total=total, offset=offset, limit=limit)


@router.get("/{order_id}", response_model=SOOut)
async def get_sales_order(
    order_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    svc = SalesOrderService(db)
    return await svc.get(order_id, user["tenant_id"])


@router.get("/{order_id}/batches", response_model=TraceBackwardOut)
async def trace_backward(
    order_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    """Trace backward: SO -> which batches were used."""
    svc = SalesOrderService(db)
    return await svc.trace_backward(order_id, user["tenant_id"])


@router.post("", response_model=SOOut, status_code=201)
async def create_sales_order(
    body: SOCreate,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    data = body.model_dump(exclude={"lines"})
    lines = [l.model_dump() for l in body.lines]
    order = await svc.create(user["tenant_id"], data, lines, user.get("id"))
    # Resolve customer name for audit
    from app.repositories.customer_repo import CustomerRepository
    customer = await CustomerRepository(db).get_by_id(data["customer_id"], user["tenant_id"])
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.create", resource_type="sales_order",
        resource_id=order.id,
        new_data={
            "order_number": order.order_number,
            "customer_name": customer.name if customer else str(data["customer_id"]),
            "total": float(order.total),
            "lines_count": len(lines),
            "currency": data.get("currency", "COP"),
        },
        ip_address=_ip(request),
    )
    return order


@router.patch("/{order_id}", response_model=SOOut)
async def update_sales_order(
    order_id: str,
    body: SOUpdate,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    old_data = {"order_number": order.order_number, "status": order.status.value if hasattr(order.status, "value") else str(order.status)}
    data = body.model_dump(exclude_unset=True)
    data["updated_by"] = user.get("id")
    from app.repositories.sales_order_repo import SalesOrderRepository
    repo = SalesOrderRepository(db)
    result = await repo.update(order, data)
    # Recalculate totals if discount was changed
    if "discount_pct" in data or "discount_reason" in data:
        from app.services.sales_order_service import recalculate_so_totals
        recalculate_so_totals(result)
        await db.flush()
        result = await svc.get(order_id, user["tenant_id"])
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.update", resource_type="sales_order",
        resource_id=order_id,
        old_data=old_data,
        new_data={"order_number": order.order_number, **body.model_dump(exclude_unset=True)},
        ip_address=_ip(request),
    )
    return result


@router.delete("/{order_id}", status_code=204)
async def delete_sales_order(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.delete", resource_type="sales_order",
        resource_id=order_id,
        old_data={"order_number": order.order_number, "status": order.status.value if hasattr(order.status, "value") else str(order.status)},
        new_data={"order_number": order.order_number},
        ip_address=_ip(request),
    )
    await svc.delete(order_id, user["tenant_id"])


@router.post("/{order_id}/confirm")
async def confirm_order(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    old_status = order.status.value if hasattr(order.status, "value") else str(order.status)
    result = await svc.confirm(order_id, user["tenant_id"], user.get("id"), user.get("name"))

    if result.get("approval_required"):
        await audit.log(
            tenant_id=user["tenant_id"], user=user,
            action="inventory.so.approval_requested", resource_type="sales_order",
            resource_id=order_id,
            old_data={"status": old_status},
            new_data={"order_number": order.order_number, "status": "pending_approval", "total": float(order.total)},
            ip_address=_ip(request),
        )
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=202,
            content={
                "status": "pending_approval",
                "message": f"SO enviado a aprobación. Total ${order.total:,.2f} supera el umbral configurado.",
                "order": SOOut.model_validate(result["order"]).model_dump(mode="json"),
                "backorder": None,
                "split_preview": result["split_preview"],
                "approval_required": True,
            },
        )

    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.confirm", resource_type="sales_order",
        resource_id=order_id,
        old_data={"status": old_status},
        new_data={
            "order_number": order.order_number,
            "status": "confirmed",
            "has_backorder": result["split_preview"]["has_backorder"],
            "backorder_id": result["backorder"].id if result["backorder"] else None,
        },
        ip_address=_ip(request),
    )
    return ConfirmWithBackorderOut(**{
        "order": result["order"],
        "backorder": result["backorder"],
        "split_preview": result["split_preview"],
    })


@router.post("/{order_id}/pick", response_model=SOOut)
async def start_picking(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    old_status = order.status.value if hasattr(order.status, "value") else str(order.status)
    result = await svc.start_picking(order_id, user["tenant_id"], user.get("id"))
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.pick", resource_type="sales_order",
        resource_id=order_id,
        old_data={"status": old_status},
        new_data={"order_number": order.order_number, "status": "picking"},
        ip_address=_ip(request),
    )
    return result


@router.post("/{order_id}/ship", response_model=SOOut)
async def ship_order(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    body: ShipRequest | None = None,
):
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    old_status = order.status.value if hasattr(order.status, "value") else str(order.status)
    line_shipments = [s.model_dump() for s in body.line_shipments] if body and body.line_shipments else None
    shipping_info = body.shipping_info.model_dump() if body and body.shipping_info else None
    result = await svc.ship(order_id, user["tenant_id"], line_shipments, shipping_info, user.get("id"))
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.ship", resource_type="sales_order",
        resource_id=order_id,
        old_data={"status": old_status},
        new_data={"order_number": order.order_number, "status": "shipped"},
        ip_address=_ip(request),
    )

    # Fire-and-forget: notify trace-service about shipped SO
    # Only if there are trace assets linked (via metadata.trace_asset_ids on SO)
    from app.clients import trace_client
    trace_asset_ids = getattr(order, "trace_asset_ids", None) or []
    if trace_asset_ids:
        tracking_number = (
            body.shipping_info.tracking_number
            if body and body.shipping_info and hasattr(body.shipping_info, "tracking_number")
            else None
        )
        await trace_client.notify_so_shipped_background(
            tenant_id=user["tenant_id"],
            so_id=order_id,
            asset_ids=trace_asset_ids,
            to_wallet_id=getattr(order, "customer_wallet_id", ""),
            tracking_number=tracking_number,
        )

    return result


@router.post("/{order_id}/deliver", response_model=SOOut)
async def deliver_order(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    old_status = order.status.value if hasattr(order.status, "value") else str(order.status)
    result = await svc.deliver(order_id, user["tenant_id"], user.get("id"))
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.deliver", resource_type="sales_order",
        resource_id=order_id,
        old_data={"status": old_status},
        new_data={"order_number": order.order_number, "status": "delivered"},
        ip_address=_ip(request),
    )
    return result


@router.post("/{order_id}/return", response_model=SOOut)
async def return_order(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    old_status = order.status.value if hasattr(order.status, "value") else str(order.status)
    result = await svc.return_order(order_id, user["tenant_id"], user.get("id"))
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.return", resource_type="sales_order",
        resource_id=order_id,
        old_data={"status": old_status},
        new_data={"order_number": order.order_number, "status": "returned"},
        ip_address=_ip(request),
    )
    return result


@router.post("/{order_id}/cancel", response_model=SOOut)
async def cancel_order(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    old_status = order.status.value if hasattr(order.status, "value") else str(order.status)
    result = await svc.cancel(order_id, user["tenant_id"], user.get("id"))
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.cancel", resource_type="sales_order",
        resource_id=order_id,
        old_data={"status": old_status},
        new_data={"order_number": order.order_number, "status": "canceled"},
        ip_address=_ip(request),
    )
    return result


@router.post("/{order_id}/retry-invoice", response_model=SOOut)
async def retry_invoice(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    """Retry electronic invoicing for a delivered order that failed."""
    svc = SalesOrderService(db)
    return await svc.retry_einvoice(order_id, user["tenant_id"])


@router.post("/{order_id}/retry-credit-note", response_model=SOOut)
async def retry_credit_note(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    """Retry credit note issuance for a returned order that failed."""
    svc = SalesOrderService(db)
    return await svc.retry_credit_note(order_id, user["tenant_id"])


@router.post("/{order_id}/debit-note", response_model=SOOut)
async def issue_debit_note(
    order_id: str,
    body: dict,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    """Issue a DIAN debit note for a price adjustment on an invoiced order."""
    svc = SalesOrderService(db)
    reason = body.get("reason", "Ajuste de precio")
    amount = body.get("amount", 0)
    return await svc.issue_debit_note(order_id, user["tenant_id"], reason, amount)


@router.post("/{order_id}/retry-debit-note", response_model=SOOut)
async def retry_debit_note(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    """Retry a failed debit note issuance."""
    svc = SalesOrderService(db)
    return await svc.retry_debit_note(order_id, user["tenant_id"])


@router.get("/{order_id}/stock-check", response_model=StockCheckResult)
async def stock_check(
    order_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    """Verify stock availability per line in its effective warehouse."""
    svc = SalesOrderService(db)
    return await svc.stock_check(order_id, user["tenant_id"])


@router.get("/{order_id}/reservations", response_model=list[StockReservationOut])
async def list_reservations(
    order_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    """List stock reservations for a sales order."""
    from app.services.reservation_service import ReservationService
    svc = ReservationService(db)
    return await svc.get_so_reservations(order_id)


@router.get("/{order_id}/remission")
async def get_remission(
    order_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    """Return all data needed to generate the remission PDF in the frontend."""
    svc = SalesOrderService(db)
    order = await svc.get(order_id, user["tenant_id"])

    if order.status not in ("shipped", "delivered"):
        raise HTTPException(
            status_code=400,
            detail="La remisión solo está disponible para órdenes despachadas o entregadas",
        )

    if not order.remission_number:
        raise HTTPException(status_code=400, detail="Esta orden no tiene remisión generada")

    # Resolve customer
    from app.repositories.customer_repo import CustomerRepository
    customer = await CustomerRepository(db).get_by_id(order.customer_id, user["tenant_id"])

    # Resolve warehouse
    from app.repositories.warehouse_repo import WarehouseRepository
    wh = None
    if order.warehouse_id:
        wh = await WarehouseRepository(db).get_by_id(order.warehouse_id, user["tenant_id"])

    # Company info from tenant config (best-effort; fall back to defaults)
    company = {
        "name": user.get("company") or user.get("tenant_name") or "Mi Empresa",
        "nit": user.get("tax_id") or user.get("tenant_id", "")[:20],
        "address": user.get("company_address") or "",
        "phone": user.get("company_phone") or "",
        "email": user.get("company_email") or user.get("email") or "",
    }

    # Build lines
    lines = []
    total_items = 0
    total_quantity = 0.0
    for line in order.lines:
        qty = float(line.qty_shipped)
        if qty <= 0:
            continue
        total_items += 1
        total_quantity += qty

        # Resolve line warehouse name
        line_wh_name = None
        if line.warehouse_id:
            line_wh = await WarehouseRepository(db).get_by_id(line.warehouse_id, user["tenant_id"])
            line_wh_name = line_wh.name if line_wh else None
        if not line_wh_name and wh:
            line_wh_name = wh.name

        # Resolve batch/serial info
        lot_number = None
        serial_number = None
        if line.batch_id:
            from app.repositories.batch_repo import BatchRepository
            batch = await BatchRepository(db).get_by_id(line.batch_id, user["tenant_id"])
            if batch:
                lot_number = batch.batch_number

        product = line.product if hasattr(line, "product") and line.product else None
        unit_price = float(line.unit_price) if line.unit_price else 0
        discount = float(line.discount_pct) if hasattr(line, "discount_pct") and line.discount_pct else 0
        line_subtotal = qty * unit_price
        line_discount_amount = line_subtotal * (discount / 100) if discount else 0
        line_total = line_subtotal - line_discount_amount
        tax_rate = float(line.tax_rate) if hasattr(line, "tax_rate") and line.tax_rate else 0
        line_tax = line_total * (tax_rate / 100) if tax_rate else 0

        lines.append({
            "product_name": (product.name if product else None) or getattr(line, "product_name", None) or line.product_id[:8],
            "product_code": (product.sku if product else None) or getattr(line, "product_sku", None) or "",
            "quantity": qty,
            "unit": (product.unit_of_measure if product else None) or "und",
            "warehouse_name": line_wh_name or "—",
            "lot_number": lot_number,
            "serial_number": serial_number,
            "unit_price": unit_price,
            "discount_pct": discount,
            "line_subtotal": round(line_subtotal, 2),
            "line_total": round(line_total, 2),
            "tax_rate": tax_rate,
            "tax_amount": round(line_tax, 2),
        })

    wh_address = {}
    if wh and wh.address:
        wh_address = wh.address if isinstance(wh.address, dict) else {}

    customer_address = ""
    if customer and customer.shipping_address:
        addr = customer.shipping_address if isinstance(customer.shipping_address, dict) else {}
        customer_address = addr.get("address_line") or addr.get("address", "")
    elif customer and customer.address:
        addr = customer.address if isinstance(customer.address, dict) else {}
        customer_address = addr.get("address_line") or addr.get("address", "")

    return {
        "remission_number": order.remission_number,
        "remission_date": order.remission_generated_at.isoformat() if order.remission_generated_at else None,
        "shipped_at": order.shipped_date.isoformat() if order.shipped_date else None,
        "company": company,
        "customer": {
            "name": customer.name if customer else "",
            "nit": (customer.tax_id if customer else "") or "",
            "address": customer_address,
            "phone": (customer.phone if customer else "") or "",
            "email": (customer.email if customer else "") or "",
            "contact_name": (customer.contact_name if customer else "") or "",
        },
        "warehouse": {
            "name": wh.name if wh else "—",
            "address": wh_address.get("address_line") or wh_address.get("address", ""),
            "city": wh_address.get("city", ""),
        },
        "so_number": order.order_number,
        "invoice_number": order.invoice_number,
        "notes": order.notes,
        "lines": lines,
        "total_items": total_items,
        "total_quantity": total_quantity,
        "subtotal": round(sum(l["line_subtotal"] for l in lines), 2),
        "total_discount": round(sum(l["line_subtotal"] - l["line_total"] for l in lines), 2),
        "total_tax": round(sum(l["tax_amount"] for l in lines), 2),
        "grand_total": round(sum(l["line_total"] + l["tax_amount"] for l in lines), 2),
    }


@router.patch("/{order_id}/discount", response_model=SOOut)
async def update_discount(
    order_id: str,
    body: SODiscountUpdate,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Apply or change the global discount on a draft SO."""
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    result = await svc.apply_discount(order_id, user["tenant_id"], body.discount_pct, body.discount_reason)
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.discount", resource_type="sales_order",
        resource_id=order_id,
        new_data={"discount_pct": body.discount_pct, "discount_reason": body.discount_reason},
        ip_address=_ip(request),
    )
    return result


@router.get("/{order_id}/backorders", response_model=list[SOOut])
async def list_backorders(
    order_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    """List all backorder children for a parent SO."""
    svc = SalesOrderService(db)
    return await svc.list_backorders(order_id, user["tenant_id"])


@router.post("/{order_id}/confirm-backorder", response_model=ConfirmWithBackorderOut)
async def confirm_backorder(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Confirm a backorder SO (re-runs stock check, may create nested backorder)."""
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    old_status = order.status.value if hasattr(order.status, "value") else str(order.status)
    result = await svc.confirm_backorder(order_id, user["tenant_id"], user.get("id"))
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.confirm_backorder", resource_type="sales_order",
        resource_id=order_id,
        old_data={"status": old_status},
        new_data={
            "order_number": order.order_number,
            "status": "confirmed",
            "is_backorder": True,
        },
        ip_address=_ip(request),
    )
    return result


@router.post("/{order_id}/approve", response_model=ConfirmWithBackorderOut)
async def approve_order(
    order_id: str,
    _module: ModuleUser,
    user: Approver,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Approve a pending SO and confirm it (reserves stock, invoices)."""
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    result = await svc.approve_and_confirm(
        order_id, user["tenant_id"], user.get("id", ""), user.get("name"),
    )
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.approve", resource_type="sales_order",
        resource_id=order_id,
        new_data={"order_number": result["order"].order_number, "status": "confirmed"},
        ip_address=_ip(request),
    )
    return ConfirmWithBackorderOut(**{
        "order": result["order"],
        "backorder": result["backorder"],
        "split_preview": result["split_preview"],
    })


@router.post("/{order_id}/reject", response_model=SOOut)
async def reject_order(
    order_id: str,
    body: RejectRequest,
    _module: ModuleUser,
    user: Approver,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Reject a pending SO."""
    from app.services.approval_service import ApprovalService
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    approval_svc = ApprovalService(db)
    await approval_svc.reject(order, user.get("id", ""), body.reason, user.get("name"))
    await db.flush()
    result = await svc.get(order_id, user["tenant_id"])
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.reject", resource_type="sales_order",
        resource_id=order_id,
        new_data={"order_number": order.order_number, "status": "rejected", "reason": body.reason},
        ip_address=_ip(request),
    )
    return result


@router.post("/{order_id}/resubmit", response_model=SOOut)
async def resubmit_order(
    order_id: str,
    _module: ModuleUser,
    user: Editor,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Re-submit a rejected SO for approval."""
    from app.services.approval_service import ApprovalService
    svc = SalesOrderService(db)
    audit = InventoryAuditService(svc.db)
    order = await svc.get(order_id, user["tenant_id"])
    approval_svc = ApprovalService(db)
    await approval_svc.resubmit(order, user.get("id", ""), user.get("name"))
    await db.flush()
    result = await svc.get(order_id, user["tenant_id"])
    await audit.log(
        tenant_id=user["tenant_id"], user=user,
        action="inventory.so.resubmit", resource_type="sales_order",
        resource_id=order_id,
        new_data={"order_number": order.order_number, "status": "pending_approval"},
        ip_address=_ip(request),
    )
    return result


@router.get("/{order_id}/approval-log", response_model=list[SOApprovalLogOut])
async def get_approval_log(
    order_id: str,
    _module: ModuleUser,
    user: Viewer,
    db: AsyncSession = Depends(get_db_session),
):
    """List the full approval history for a SO."""
    from app.services.approval_service import ApprovalService
    svc = SalesOrderService(db)
    await svc.get(order_id, user["tenant_id"])  # ensure exists + tenant
    approval_svc = ApprovalService(db)
    return await approval_svc.get_approval_log(order_id)


@router.patch("/{order_id}/lines/{line_id}/warehouse", response_model=SOOut)
async def update_line_warehouse(
    order_id: str,
    line_id: str,
    body: LineWarehouseUpdate,
    _module: ModuleUser,
    user: Editor,
    db: AsyncSession = Depends(get_db_session),
):
    """Update the warehouse for a specific SO line (draft/confirmed only)."""
    svc = SalesOrderService(db)
    return await svc.update_line_warehouse(order_id, line_id, body.warehouse_id, user["tenant_id"])
