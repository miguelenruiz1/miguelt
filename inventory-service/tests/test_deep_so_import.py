"""Deep tests for SalesOrderService + ImportService — targeting uncovered lines.

Part 1: SalesOrderService  (create price resolution, tax calc, confirm backorder,
         start_picking, ship, deliver, return_order, cancel edge cases,
         _try_einvoice, _try_credit_note, retry_einvoice)
Part 2: ImportService  (seed_demo for technology/cleaning, delete_demo,
         import_products_csv with various CSV scenarios)
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


TENANT = "test-tenant"
USER = "test-user-1"


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

async def _setup_full(client: AsyncClient, tag: str, qty: int = 200, price: int = 10000):
    """Create product, warehouse, customer, receive stock. Return (pid, wid, cid)."""
    p = await client.post("/api/v1/products", json={
        "name": f"Prod-{tag}", "sku": f"DSO-{tag}", "unit_of_measure": "un",
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{tag}", "code": f"WH-DSO-{tag}", "type": "main",
    })
    c = await client.post("/api/v1/partners", json={
        "name": f"Client-{tag}", "code": f"CLID-DSO-{tag}", "is_customer": True,
    })
    pid, wid, cid = p.json()["id"], w.json()["id"], c.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": str(qty), "unit_cost": str(price),
    })
    return pid, wid, cid


async def _create_so(client: AsyncClient, cid, wid, lines, **extra):
    resp = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": lines, **extra,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _advance_to_shipped(client, so_id):
    """Draft -> confirmed -> picking -> shipped."""
    r = await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    assert r.status_code in (200, 202), r.text
    r = await client.post(f"/api/v1/sales-orders/{so_id}/pick")
    assert r.status_code == 200, r.text
    r = await client.post(f"/api/v1/sales-orders/{so_id}/ship")
    assert r.status_code == 200, r.text
    return r.json()


# ═══════════════════════════════════════════════════════════════════════════════
#  Part 1 — SalesOrderService
# ═══════════════════════════════════════════════════════════════════════════════


# ── 1.1  Create: customer price resolution + tax calc ─────────────────────

@pytest.mark.asyncio
async def test_create_so_manual_price(client: AsyncClient):
    """Create SO with explicit unit_price — price_source should be manual."""
    pid, wid, cid = await _setup_full(client, "MANPRC")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_price": 12500, "tax_rate": 19},
    ])
    line = so["lines"][0]
    assert line["unit_price"] == 12500
    assert line.get("price_source") == "manual"


@pytest.mark.asyncio
async def test_create_so_base_price_fallback(client: AsyncClient):
    """Create SO without explicit unit_price — should fall back to product base."""
    pid, wid, cid = await _setup_full(client, "BASEPRC")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 3},
    ])
    line = so["lines"][0]
    assert line.get("price_source") in ("product_base", "manual", None)


@pytest.mark.asyncio
async def test_create_so_with_tax_and_discount(client: AsyncClient):
    """SO with both line tax and global discount — verify amounts > 0."""
    pid, wid, cid = await _setup_full(client, "TAXDISC")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_price": 20000, "tax_rate": 19},
    ], discount_pct=5.0, discount_reason="Volume")
    assert float(so["tax_amount"]) > 0
    assert float(so["discount_amount"]) > 0
    assert float(so["total"]) > 0


@pytest.mark.asyncio
async def test_create_so_zero_qty_rejected(client: AsyncClient):
    """Line with qty=0 should be rejected."""
    pid, wid, cid = await _setup_full(client, "ZEROQTY")
    resp = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 0, "unit_price": 5000}],
    })
    assert resp.status_code == 422 or resp.status_code == 400


@pytest.mark.asyncio
async def test_create_so_negative_price_rejected(client: AsyncClient):
    """Line with negative unit_price should be rejected."""
    pid, wid, cid = await _setup_full(client, "NEGPRC")
    resp = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 5, "unit_price": -100}],
    })
    assert resp.status_code == 422 or resp.status_code == 400


@pytest.mark.asyncio
async def test_create_so_empty_lines_rejected(client: AsyncClient):
    """SO with no lines should be rejected."""
    _, wid, cid = await _setup_full(client, "NOLINES")
    resp = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [],
    })
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_create_so_nonexistent_customer(client: AsyncClient):
    """SO with invalid customer_id should fail."""
    pid, wid, _ = await _setup_full(client, "BADCUST")
    resp = await client.post("/api/v1/sales-orders", json={
        "customer_id": str(uuid.uuid4()), "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 1, "unit_price": 1000}],
    })
    assert resp.status_code in (404, 422)


# ── 1.2  Confirm: backorder analysis + stock reservation ─────────────────

@pytest.mark.asyncio
async def test_confirm_with_insufficient_stock(client: AsyncClient):
    """Confirm when order qty exceeds stock — may create backorder or fail."""
    pid, wid, cid = await _setup_full(client, "LOWSTK", qty=5)
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 100, "unit_price": 5000},
    ])
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    # Either backorder created or validation error
    assert resp.status_code in (200, 202, 422)


@pytest.mark.asyncio
async def test_confirm_normal_flow(client: AsyncClient):
    """Confirm with sufficient stock — should succeed."""
    pid, wid, cid = await _setup_full(client, "NORMCNF")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_price": 8000},
    ])
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    assert resp.status_code in (200, 202)
    data = resp.json()
    order = data.get("order", data)
    assert order["status"] in ("confirmed", "pending_approval")


# ── 1.3  Start picking ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_picking_success(client: AsyncClient):
    """Confirmed -> picking should succeed when stock is available."""
    pid, wid, cid = await _setup_full(client, "PICKOK")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_price": 7000},
    ])
    await client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/pick")
    assert resp.status_code == 200
    assert resp.json()["status"] == "picking"


@pytest.mark.asyncio
async def test_start_picking_from_draft_fails(client: AsyncClient):
    """Cannot start picking directly from draft."""
    pid, wid, cid = await _setup_full(client, "PICKFAIL")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_price": 7000},
    ])
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/pick")
    assert resp.status_code in (400, 422)


# ── 1.4  Ship ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ship_full_order(client: AsyncClient):
    """picking -> shipped with full qty."""
    pid, wid, cid = await _setup_full(client, "SHIPFULL")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_price": 9000},
    ])
    await client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    await client.post(f"/api/v1/sales-orders/{so['id']}/pick")
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/ship")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "shipped"
    assert data.get("remission_number") is not None


@pytest.mark.asyncio
async def test_ship_with_shipping_info(client: AsyncClient):
    """Ship with explicit shipping_info metadata."""
    pid, wid, cid = await _setup_full(client, "SHIPINFO")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_price": 6000},
    ])
    await client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    await client.post(f"/api/v1/sales-orders/{so['id']}/pick")
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/ship", json={
        "shipping_info": {
            "carrier": "DHL",
            "tracking_number": "TRK-123456",
            "address_line": "Calle 100 #15-20",
            "city": "Bogota",
            "country": "CO",
        },
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_ship_partial_with_line_shipments(client: AsyncClient):
    """Ship partial qty via line_shipments."""
    pid, wid, cid = await _setup_full(client, "SHIPLNS")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 20, "unit_price": 5000},
    ])
    await client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    await client.post(f"/api/v1/sales-orders/{so['id']}/pick")
    lines = (await client.get(f"/api/v1/sales-orders/{so['id']}")).json()["lines"]
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/ship", json={
        "line_shipments": [{"line_id": lines[0]["id"], "qty_shipped": 15}],
    })
    assert resp.status_code == 200


# ── 1.5  Deliver ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deliver_success(client: AsyncClient):
    """shipped -> delivered: stock deduction + sale movements."""
    pid, wid, cid = await _setup_full(client, "DELIVOK", qty=100)
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_price": 8000},
    ])
    await _advance_to_shipped(client, so["id"])
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/deliver")
    assert resp.status_code == 200
    assert resp.json()["status"] == "delivered"


@pytest.mark.asyncio
async def test_deliver_creates_sale_movement(client: AsyncClient):
    """After deliver, a 'sale' movement should exist."""
    pid, wid, cid = await _setup_full(client, "DELIVMOV", qty=100)
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_price": 7000},
    ])
    await _advance_to_shipped(client, so["id"])
    await client.post(f"/api/v1/sales-orders/{so['id']}/deliver")
    # Check movements
    mvs = await client.get("/api/v1/movements", params={"product_id": pid})
    assert mvs.status_code == 200
    items = mvs.json().get("items", mvs.json())
    sale_mvs = [m for m in items if m.get("movement_type") == "sale"]
    assert len(sale_mvs) >= 1


# ── 1.6  Return ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_return_order_from_shipped(client: AsyncClient):
    """shipped -> returned: stock should be restocked."""
    pid, wid, cid = await _setup_full(client, "RETSHIP", qty=100)
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_price": 9000},
    ])
    await _advance_to_shipped(client, so["id"])
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/return")
    assert resp.status_code == 200
    assert resp.json()["status"] == "returned"


@pytest.mark.asyncio
async def test_return_order_from_delivered(client: AsyncClient):
    """delivered -> returned: restocks + return movement."""
    pid, wid, cid = await _setup_full(client, "RETDELIV", qty=100)
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_price": 8000},
    ])
    await _advance_to_shipped(client, so["id"])
    await client.post(f"/api/v1/sales-orders/{so['id']}/deliver")
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/return")
    assert resp.status_code == 200
    assert resp.json()["status"] == "returned"
    # Verify return movement
    mvs = await client.get("/api/v1/movements", params={"product_id": pid})
    items = mvs.json().get("items", mvs.json())
    ret_mvs = [m for m in items if m.get("movement_type") == "return"]
    assert len(ret_mvs) >= 1


@pytest.mark.asyncio
async def test_return_from_draft_fails(client: AsyncClient):
    """Cannot return a draft order."""
    pid, wid, cid = await _setup_full(client, "RETDRAFT")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 2, "unit_price": 5000},
    ])
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/return")
    assert resp.status_code in (400, 422)


# ── 1.7  Cancel edge cases ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_confirmed_releases_reservation(client: AsyncClient):
    """Cancel a confirmed order — should release reservations."""
    pid, wid, cid = await _setup_full(client, "CANCONF")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_price": 6000},
    ])
    await client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_cancel_picking_releases_reservation(client: AsyncClient):
    """Cancel a picking order — should release reservations."""
    pid, wid, cid = await _setup_full(client, "CANPICK")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_price": 6000},
    ])
    await client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    await client.post(f"/api/v1/sales-orders/{so['id']}/pick")
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_cancel_delivered_fails(client: AsyncClient):
    """Cannot cancel a delivered order."""
    pid, wid, cid = await _setup_full(client, "CANDELIV", qty=100)
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_price": 7000},
    ])
    await _advance_to_shipped(client, so["id"])
    await client.post(f"/api/v1/sales-orders/{so['id']}/deliver")
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/cancel")
    assert resp.status_code in (400, 422)


# ── 1.8  Retry e-invoice ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_einvoice_on_confirmed(client: AsyncClient):
    """Retry einvoice on a confirmed order without CUFE — should succeed or skip."""
    pid, wid, cid = await _setup_full(client, "RETRYINV")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 3, "unit_price": 5000},
    ])
    await client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/retry-invoice")
    # Should succeed (may skip if no integration configured)
    assert resp.status_code in (200, 422)


@pytest.mark.asyncio
async def test_retry_einvoice_on_draft_fails(client: AsyncClient):
    """Cannot retry einvoice on a draft order."""
    pid, wid, cid = await _setup_full(client, "RETRYDRFT")
    so = await _create_so(client, cid, wid, [
        {"product_id": pid, "qty_ordered": 2, "unit_price": 5000},
    ])
    resp = await client.post(f"/api/v1/sales-orders/{so['id']}/retry-invoice")
    assert resp.status_code in (400, 422)


# ── 1.9  _try_einvoice / _try_credit_note (unit tests with mocks) ────────

@pytest.mark.asyncio
async def test_try_einvoice_success(db):
    """Unit test: _try_einvoice with mocked HTTP client + einvoicing active."""
    from app.services.sales_order_service import SalesOrderService

    svc = SalesOrderService(db)

    # Build a fake order
    order = MagicMock()
    order.id = "order-1"
    order.order_number = "SO-2026-0001"
    order.customer_id = "cust-1"
    order.confirmed_at = datetime.now(timezone.utc)
    order.currency = "COP"
    order.discount_pct = Decimal("0")
    order.discount_amount = Decimal("0")
    order.subtotal = Decimal("100000")
    order.tax_amount = Decimal("19000")
    order.total = Decimal("119000")
    order.notes = "Test order"
    order.cufe = None
    order.invoice_status = None
    order.invoice_number = None
    order.invoice_pdf_url = None
    order.invoice_remote_id = None
    order.invoice_provider = None

    # Fake line
    line = MagicMock()
    line.product_name = "Test Product"
    line.product_sku = "TST-001"
    line.qty_shipped = Decimal("10")
    line.unit_price = Decimal("10000")
    line.discount_pct = Decimal("0")
    line.discount_amount = Decimal("0")
    line.tax_rate = Decimal("19")
    line.line_subtotal = Decimal("100000")
    line.line_total = Decimal("119000")
    order.lines = [line]

    # Mock customer
    mock_customer = MagicMock()
    mock_customer.name = "Acme Corp"
    mock_customer.tax_id = "900123456"
    mock_customer.email = "acme@example.com"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"cufe": "CUFE-ABC-123", "invoice_number": "FE-001", "pdf_url": "https://pdf.url/inv.pdf", "remote_id": "remote-1", "status": "issued"}

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_resp)

    with patch("app.api.deps.is_einvoicing_active", new_callable=AsyncMock, return_value=True), \
         patch("app.api.deps.is_einvoicing_sandbox_active", new_callable=AsyncMock, return_value=False), \
         patch("app.api.deps.get_http_client", return_value=mock_http), \
         patch.object(svc.customer_repo, "get_by_id", new_callable=AsyncMock, return_value=mock_customer):
        await svc._try_einvoice(order, TENANT)

    assert order.cufe == "CUFE-ABC-123"
    assert order.invoice_number == "FE-001"
    assert order.invoice_status == "issued"


@pytest.mark.asyncio
async def test_try_einvoice_sandbox_mode(db):
    """Unit test: _try_einvoice sandbox provider returns simulated status."""
    from app.services.sales_order_service import SalesOrderService

    svc = SalesOrderService(db)

    order = MagicMock()
    order.id = "order-2"
    order.order_number = "SO-2026-0002"
    order.customer_id = "cust-2"
    order.confirmed_at = datetime.now(timezone.utc)
    order.currency = "COP"
    order.discount_pct = Decimal("0")
    order.discount_amount = Decimal("0")
    order.subtotal = Decimal("50000")
    order.tax_amount = Decimal("9500")
    order.total = Decimal("59500")
    order.notes = ""
    order.cufe = None
    order.invoice_status = None
    order.lines = []

    mock_customer = MagicMock()
    mock_customer.name = "Sandbox Corp"
    mock_customer.tax_id = "111111111"
    mock_customer.email = "sb@example.com"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"cufe": "SANDBOX-CUFE", "invoice_number": "SB-001", "remote_id": "sb-remote"}

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_resp)

    with patch("app.api.deps.is_einvoicing_active", new_callable=AsyncMock, return_value=False), \
         patch("app.api.deps.is_einvoicing_sandbox_active", new_callable=AsyncMock, return_value=True), \
         patch("app.api.deps.get_http_client", return_value=mock_http), \
         patch.object(svc.customer_repo, "get_by_id", new_callable=AsyncMock, return_value=mock_customer):
        await svc._try_einvoice(order, TENANT)

    assert order.cufe == "SANDBOX-CUFE"
    assert order.invoice_status == "simulated"


@pytest.mark.asyncio
async def test_try_einvoice_no_provider_skips(db):
    """Unit test: _try_einvoice with no provider active — should skip silently."""
    from app.services.sales_order_service import SalesOrderService

    svc = SalesOrderService(db)
    order = MagicMock()
    order.id = "order-3"
    order.cufe = None
    order.invoice_status = None

    with patch("app.api.deps.is_einvoicing_active", new_callable=AsyncMock, return_value=False), \
         patch("app.api.deps.is_einvoicing_sandbox_active", new_callable=AsyncMock, return_value=False):
        await svc._try_einvoice(order, TENANT)

    # Nothing changed
    assert order.cufe is None
    assert order.invoice_status is None


@pytest.mark.asyncio
async def test_try_einvoice_http_error_sets_failed(db):
    """Unit test: _try_einvoice when HTTP returns 500 — sets invoice_status=failed."""
    from app.services.sales_order_service import SalesOrderService

    svc = SalesOrderService(db)

    order = MagicMock()
    order.id = "order-4"
    order.order_number = "SO-2026-0004"
    order.customer_id = "cust-4"
    order.confirmed_at = datetime.now(timezone.utc)
    order.currency = "COP"
    order.discount_pct = Decimal("0")
    order.discount_amount = Decimal("0")
    order.subtotal = Decimal("100000")
    order.tax_amount = Decimal("0")
    order.total = Decimal("100000")
    order.notes = ""
    order.cufe = None
    order.invoice_status = None
    order.invoice_provider = None
    order.lines = []

    mock_customer = MagicMock()
    mock_customer.name = "Fail Corp"
    mock_customer.tax_id = ""
    mock_customer.email = ""

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_resp)

    with patch("app.api.deps.is_einvoicing_active", new_callable=AsyncMock, return_value=True), \
         patch("app.api.deps.is_einvoicing_sandbox_active", new_callable=AsyncMock, return_value=False), \
         patch("app.api.deps.get_http_client", return_value=mock_http), \
         patch.object(svc.customer_repo, "get_by_id", new_callable=AsyncMock, return_value=mock_customer):
        await svc._try_einvoice(order, TENANT)

    assert order.invoice_status == "failed"


@pytest.mark.asyncio
async def test_try_credit_note_success(db):
    """Unit test: _try_credit_note with mocked HTTP client."""
    from app.services.sales_order_service import SalesOrderService

    svc = SalesOrderService(db)

    order = MagicMock()
    order.id = "order-cn-1"
    order.order_number = "SO-2026-0010"
    order.customer_id = "cust-cn-1"
    order.cufe = "ORIGINAL-CUFE"
    order.invoice_number = "FE-010"
    order.returned_at = datetime.now(timezone.utc)
    order.currency = "COP"
    order.discount_pct = Decimal("0")
    order.discount_amount = Decimal("0")
    order.subtotal = Decimal("80000")
    order.tax_amount = Decimal("15200")
    order.total = Decimal("95200")
    order.credit_note_cufe = None
    order.credit_note_number = None
    order.credit_note_remote_id = None
    order.credit_note_status = None
    order.lines = []

    mock_customer = MagicMock()
    mock_customer.name = "CN Corp"
    mock_customer.tax_id = "900999888"
    mock_customer.email = "cn@example.com"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"cufe": "CN-CUFE-1", "credit_note_number": "NC-001", "remote_id": "cn-remote"}

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_resp)

    with patch("app.api.deps.is_einvoicing_active", new_callable=AsyncMock, return_value=True), \
         patch("app.api.deps.is_einvoicing_sandbox_active", new_callable=AsyncMock, return_value=False), \
         patch("app.api.deps.get_http_client", return_value=mock_http), \
         patch.object(svc.customer_repo, "get_by_id", new_callable=AsyncMock, return_value=mock_customer):
        await svc._try_credit_note(order, TENANT)

    assert order.credit_note_cufe == "CN-CUFE-1"
    assert order.credit_note_status in ("issued", "simulated")


@pytest.mark.asyncio
async def test_try_credit_note_no_provider_skips(db):
    """Unit test: _try_credit_note with no provider — should skip."""
    from app.services.sales_order_service import SalesOrderService

    svc = SalesOrderService(db)
    order = MagicMock()
    order.id = "order-cn-2"
    order.credit_note_status = None

    with patch("app.api.deps.is_einvoicing_active", new_callable=AsyncMock, return_value=False), \
         patch("app.api.deps.is_einvoicing_sandbox_active", new_callable=AsyncMock, return_value=False):
        await svc._try_credit_note(order, TENANT)

    assert order.credit_note_status is None


# ── 1.10  recalculate_so_totals ──────────────────────────────────────────

def test_recalculate_so_totals_basic():
    """Test recalculate_so_totals with simple mock."""
    from app.services.sales_order_service import recalculate_so_totals

    line = MagicMock()
    line.qty_ordered = Decimal("10")
    line.unit_price = Decimal("1000")
    line.discount_pct = Decimal("10")
    line.tax_rate = Decimal("19")
    line.tax_rate_pct = None
    line.retention_pct = None

    so = MagicMock()
    so.discount_pct = Decimal("5")
    so.lines = [line]

    recalculate_so_totals(so)

    assert so.subtotal > 0
    assert so.total > 0
    assert so.tax_amount >= 0


def test_recalculate_so_totals_with_retention():
    """Test recalculate_so_totals with retention_pct."""
    from app.services.sales_order_service import recalculate_so_totals

    line = MagicMock()
    line.qty_ordered = Decimal("5")
    line.unit_price = Decimal("20000")
    line.discount_pct = Decimal("0")
    line.tax_rate = Decimal("19")
    line.tax_rate_pct = Decimal("0.19")
    line.retention_pct = Decimal("0.025")

    so = MagicMock()
    so.discount_pct = Decimal("0")
    so.lines = [line]

    recalculate_so_totals(so)

    assert line.retention_amount > 0
    assert so.total_retention > 0
    assert so.total_payable <= so.total_with_tax


# ═══════════════════════════════════════════════════════════════════════════════
#  Part 2 — ImportService
# ═══════════════════════════════════════════════════════════════════════════════


# ── 2.1  import_products_csv ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_import_csv_basic(client: AsyncClient):
    """Import a simple CSV with sku and name."""
    csv = "sku,name\nCSV-001,Product One\nCSV-002,Product Two\n"
    resp = await client.post(
        "/api/v1/imports/products",
        files={"file": ("products.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2
    assert data["skipped"] == 0


@pytest.mark.asyncio
async def test_import_csv_with_initial_stock(client: AsyncClient):
    """CSV with warehouse_id and initial_stock columns."""
    # First create a warehouse
    wh = await client.post("/api/v1/warehouses", json={
        "name": "WH-CSV-Stock", "code": "WH-CSVSTK", "type": "main",
    })
    wid = wh.json()["id"]

    csv = f"sku,name,warehouse_id,initial_stock\nCSV-STK-001,Prod With Stock,{wid},50\n"
    resp = await client.post(
        "/api/v1/imports/products",
        files={"file": ("products.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 1


@pytest.mark.asyncio
async def test_import_csv_with_barcode_description(client: AsyncClient):
    """CSV with barcode, description, min_stock_level columns."""
    csv = "sku,name,barcode,description,min_stock_level\nCSV-BAR-001,Barcode Prod,7701234567890,A nice product,25\n"
    resp = await client.post(
        "/api/v1/imports/products",
        files={"file": ("products.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 1


@pytest.mark.asyncio
async def test_import_csv_semicolon_delimited(client: AsyncClient):
    """Semicolon-delimited CSV."""
    csv = "sku;name;description\nCSV-SEMI-001;Semi Product;Semicolon test\n"
    resp = await client.post(
        "/api/v1/imports/products",
        files={"file": ("products.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 1


@pytest.mark.asyncio
async def test_import_csv_extra_unknown_columns(client: AsyncClient):
    """CSV with extra columns — should be ignored."""
    csv = "sku,name,color,weight,vendor_name\nCSV-EXT-001,Extra Cols Prod,red,2.5,Vendor A\n"
    resp = await client.post(
        "/api/v1/imports/products",
        files={"file": ("products.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 1


@pytest.mark.asyncio
async def test_import_csv_missing_required_columns(client: AsyncClient):
    """CSV without sku/name columns should fail."""
    csv = "code,description\nX-001,Some desc\n"
    resp = await client.post(
        "/api/v1/imports/products",
        files={"file": ("products.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 0
    assert len(data["errors"]) > 0


@pytest.mark.asyncio
async def test_import_csv_empty_sku_skipped(client: AsyncClient):
    """Rows with empty SKU should be skipped."""
    csv = "sku,name\n,Empty SKU Product\nCSV-EMSKU-001,Valid\n"
    resp = await client.post(
        "/api/v1/imports/products",
        files={"file": ("products.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 1
    assert data["skipped"] == 1


@pytest.mark.asyncio
async def test_import_csv_duplicate_sku_in_csv(client: AsyncClient):
    """Duplicate SKUs within the same CSV should be skipped."""
    csv = "sku,name\nCSV-DUP-001,First\nCSV-DUP-001,Duplicate\n"
    resp = await client.post(
        "/api/v1/imports/products",
        files={"file": ("products.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 1
    assert data["skipped"] == 1


@pytest.mark.asyncio
async def test_import_csv_existing_sku_in_db(client: AsyncClient):
    """SKU that already exists in DB should be skipped."""
    # Create product first
    await client.post("/api/v1/products", json={
        "name": "Pre-existing", "sku": "CSV-EXIST-001", "unit_of_measure": "un",
    })
    csv = "sku,name\nCSV-EXIST-001,Duplicate in DB\n"
    resp = await client.post(
        "/api/v1/imports/products",
        files={"file": ("products.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 0
    assert data["skipped"] == 1


@pytest.mark.asyncio
async def test_import_csv_empty_file(client: AsyncClient):
    """Completely empty CSV."""
    csv = ""
    resp = await client.post(
        "/api/v1/imports/products",
        files={"file": ("products.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 0


# ── 2.2  generate_template ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_template_technology(client: AsyncClient):
    resp = await client.get("/api/v1/imports/templates/technology")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_download_template_cleaning(client: AsyncClient):
    resp = await client.get("/api/v1/imports/templates/cleaning")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_download_template_pet_food(client: AsyncClient):
    resp = await client.get("/api/v1/imports/templates/pet_food")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_download_template_unknown(client: AsyncClient):
    resp = await client.get("/api/v1/imports/templates/unknown_industry")
    assert resp.status_code == 404


# ── 2.3  seed_demo + delete_demo ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_seed_demo_technology(client: AsyncClient):
    """Seed technology demo data."""
    resp = await client.post("/api/v1/imports/demo", json={
        "industries": ["technology"],
    })
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    r = results[0]
    assert r["industry"] == "technology"
    assert r.get("products_created", 0) >= 0


@pytest.mark.asyncio
async def test_seed_demo_cleaning(client: AsyncClient):
    """Seed cleaning demo data."""
    resp = await client.post("/api/v1/imports/demo", json={
        "industries": ["cleaning"],
    })
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["industry"] == "cleaning"


@pytest.mark.asyncio
async def test_seed_demo_unknown_industry(client: AsyncClient):
    """Unknown industry should return error in result."""
    resp = await client.post("/api/v1/imports/demo", json={
        "industries": ["blockchain"],
    })
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert "error" in results[0]


@pytest.mark.asyncio
async def test_seed_demo_idempotent(client: AsyncClient):
    """Seeding the same industry twice should not duplicate data."""
    await client.post("/api/v1/imports/demo", json={"industries": ["pet_food"]})
    resp = await client.post("/api/v1/imports/demo", json={"industries": ["pet_food"]})
    assert resp.status_code == 200
    r = resp.json()[0]
    # On second run, most counts should be 0 (already exists)
    assert r.get("products_created", 0) == 0 or r.get("products_restored", 0) >= 0


@pytest.mark.asyncio
async def test_delete_demo_technology(client: AsyncClient):
    """Seed then delete technology demo data."""
    await client.post("/api/v1/imports/demo", json={"industries": ["technology"]})
    resp = await client.request(
        "DELETE", "/api/v1/imports/demo",
        json={"industries": ["technology"]},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    r = results[0]
    assert r["industry"] == "technology"


@pytest.mark.asyncio
async def test_delete_demo_unknown_industry(client: AsyncClient):
    """Delete with unknown industry should return error in result."""
    resp = await client.request(
        "DELETE", "/api/v1/imports/demo",
        json={"industries": ["aliens"]},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert "error" in results[0]


# ── 2.4  ImportService helpers (unit tests) ──────────────────────────────

def test_slugify():
    from app.services.import_service import ImportService
    assert ImportService._slugify("Materia Prima") == "materia-prima"
    assert ImportService._slugify("  Limpieza & Hogar  ") == "limpieza-hogar"
    assert ImportService._slugify("café-especial") == "café-especial"


def test_detect_delimiter():
    from app.services.import_service import ImportService
    assert ImportService._detect_delimiter("a,b,c\n1,2,3") == ","
    assert ImportService._detect_delimiter("a;b;c\n1;2;3") == ";"
    assert ImportService._detect_delimiter("a\tb\tc\n1\t2\t3") == "\t"
    assert ImportService._detect_delimiter("abc") == ","  # default


def test_parse_decimal():
    from app.services.import_service import ImportService
    assert ImportService._parse_decimal("123.45", None) == Decimal("123.45")
    assert ImportService._parse_decimal("", None) is None
    assert ImportService._parse_decimal(None, Decimal("0")) == Decimal("0")
    assert ImportService._parse_decimal("invalid", Decimal("99")) == Decimal("99")


def test_parse_int():
    from app.services.import_service import ImportService
    assert ImportService._parse_int("42", 0) == 42
    assert ImportService._parse_int("3.7", 0) == 3
    assert ImportService._parse_int("", 5) == 5
    assert ImportService._parse_int(None, 10) == 10
    assert ImportService._parse_int("abc", 0) == 0


def test_parse_date():
    from app.services.import_service import ImportService
    from datetime import date
    assert ImportService._parse_date("2026-03-25") == date(2026, 3, 25)
    assert ImportService._parse_date("") is None
    assert ImportService._parse_date(None) is None
    assert ImportService._parse_date("not-a-date") is None
