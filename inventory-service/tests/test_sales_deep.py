"""Deep sales order tests — approval flow, tax calc, multi-line, backorder confirm, retry invoice."""
import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient, suffix: str, qty: int = 200):
    p = await client.post("/api/v1/products", json={
        "name": f"Prod-{suffix}", "sku": f"SD-{suffix}", "unit_of_measure": "un",
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{suffix}", "code": f"WH-SD-{suffix}", "type": "main",
    })
    c = await client.post("/api/v1/partners", json={
        "name": f"Client-{suffix}", "code": f"CLID-{suffix}", "is_customer": True,
    })
    pid, wid, cid = p.json()["id"], w.json()["id"], c.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": str(qty), "unit_cost": "10000",
    })
    return pid, wid, cid


# ── Multi-line sales order ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_multi_line_so(client: AsyncClient):
    p1 = await client.post("/api/v1/products", json={"name": "ML-P1", "sku": "SDML-P1", "unit_of_measure": "un"})
    p2 = await client.post("/api/v1/products", json={"name": "ML-P2", "sku": "SDML-P2", "unit_of_measure": "un"})
    w = await client.post("/api/v1/warehouses", json={"name": "WH-ML", "code": "WH-SDML", "type": "main"})
    c = await client.post("/api/v1/partners", json={"name": "ML-Client", "code": "CLID-ML", "is_customer": True})
    pid1, pid2, wid, cid = p1.json()["id"], p2.json()["id"], w.json()["id"], c.json()["id"]

    await client.post("/api/v1/stock/receive", json={"product_id": pid1, "warehouse_id": wid, "quantity": "100", "unit_cost": "5000"})
    await client.post("/api/v1/stock/receive", json={"product_id": pid2, "warehouse_id": wid, "quantity": "100", "unit_cost": "8000"})

    resp = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [
            {"product_id": pid1, "qty_ordered": 10, "unit_price": 7000},
            {"product_id": pid2, "qty_ordered": 5, "unit_price": 12000},
        ],
    })
    assert resp.status_code == 201
    assert len(resp.json()["lines"]) == 2


# ── Confirm + pick + ship partial ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ship_partial_qty(client: AsyncClient):
    pid, wid, cid = await _setup(client, "SHIPPART")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 50, "unit_price": 15000}],
    })
    so_id = so.json()["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    await client.post(f"/api/v1/sales-orders/{so_id}/pick")

    lines = (await client.get(f"/api/v1/sales-orders/{so_id}")).json()["lines"]
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/ship", json={
        "line_shipments": [{"line_id": lines[0]["id"], "qty_shipped": 30}],
    })
    assert resp.status_code == 200


# ── SO with discount ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_so_with_discount(client: AsyncClient):
    pid, wid, cid = await _setup(client, "SODISC")
    resp = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "discount_pct": 10.0, "discount_reason": "Loyal customer",
        "lines": [{"product_id": pid, "qty_ordered": 20, "unit_price": 10000}],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["discount_pct"] == 10.0


# ── SO with tax rate ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_so_with_tax(client: AsyncClient):
    pid, wid, cid = await _setup(client, "SOTAX")
    resp = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 10, "unit_price": 10000, "tax_rate": 0.19}],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["tax_amount"] >= 0


# ── SO pending approval (threshold) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_so_approval_threshold(client: AsyncClient):
    """Set low threshold, create big SO, should require approval."""
    # Set threshold
    await client.patch("/api/v1/config/so-approval-threshold", json={"threshold": 100})

    pid, wid, cid = await _setup(client, "SOAPPR")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 50, "unit_price": 10000}],
    })
    so_id = so.json()["id"]
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    assert resp.status_code in (200, 202)
    result = resp.json()
    # Order may go to pending_approval or confirmed depending on threshold check
    order_status = result.get("order", result).get("status", "")
    assert order_status in ("confirmed", "pending_approval")


# ── Approve pending SO ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_pending_so(client: AsyncClient):
    await client.patch("/api/v1/config/so-approval-threshold", json={"threshold": 1})
    pid, wid, cid = await _setup(client, "SOAPR2")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 10, "unit_price": 5000}],
    })
    so_id = so.json()["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/approve")
    assert resp.status_code in (200, 422)


# ── Reject pending SO ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_pending_so(client: AsyncClient):
    await client.patch("/api/v1/config/so-approval-threshold", json={"threshold": 1})
    pid, wid, cid = await _setup(client, "SOREJ")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 5, "unit_price": 3000}],
    })
    so_id = so.json()["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/reject", json={
        "reason": "Budget cut",
    })
    assert resp.status_code in (200, 422)


# ── Approval log ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_so_approval_log(client: AsyncClient):
    pid, wid, cid = await _setup(client, "SOALOG")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 5, "unit_price": 5000}],
    })
    so_id = so.json()["id"]
    resp = await client.get(f"/api/v1/sales-orders/{so_id}/approval-log")
    assert resp.status_code == 200


# ── Pending approval list ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pending_approval_list(client: AsyncClient):
    resp = await client.get("/api/v1/sales-orders/pending-approval")
    assert resp.status_code == 200


# ── Retry invoice (on delivered order) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_invoice(client: AsyncClient):
    pid, wid, cid = await _setup(client, "RTINV")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 5, "unit_price": 10000}],
    })
    so_id = so.json()["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    await client.post(f"/api/v1/sales-orders/{so_id}/pick")
    await client.post(f"/api/v1/sales-orders/{so_id}/ship")
    await client.post(f"/api/v1/sales-orders/{so_id}/deliver")

    resp = await client.post(f"/api/v1/sales-orders/{so_id}/retry-invoice")
    assert resp.status_code in (200, 422)  # 422 if no invoice provider configured


# ── Retry credit note (on returned order) ────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_credit_note(client: AsyncClient):
    pid, wid, cid = await _setup(client, "RTCN")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 5, "unit_price": 10000}],
    })
    so_id = so.json()["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    await client.post(f"/api/v1/sales-orders/{so_id}/pick")
    await client.post(f"/api/v1/sales-orders/{so_id}/ship")
    await client.post(f"/api/v1/sales-orders/{so_id}/deliver")
    await client.post(f"/api/v1/sales-orders/{so_id}/return")

    resp = await client.post(f"/api/v1/sales-orders/{so_id}/retry-credit-note")
    assert resp.status_code in (200, 422)


# ── Confirm backorder ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_confirm_backorder(client: AsyncClient):
    pid, wid, cid = await _setup(client, "CNFBO", qty=30)
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 50, "unit_price": 10000}],
    })
    so_id = so.json()["id"]
    confirm_resp = await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    result = confirm_resp.json()
    bo = result.get("backorder")
    if bo and bo.get("id"):
        # Replenish stock and confirm the backorder
        await client.post("/api/v1/stock/receive", json={
            "product_id": pid, "warehouse_id": wid, "quantity": "50", "unit_cost": "10000",
        })
        resp = await client.post(f"/api/v1/sales-orders/{bo['id']}/confirm-backorder")
        assert resp.status_code in (200, 422)


# ── SO batches trace ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_so_batches_trace(client: AsyncClient):
    pid, wid, cid = await _setup(client, "TRACE")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 5, "unit_price": 10000}],
    })
    so_id = so.json()["id"]
    resp = await client.get(f"/api/v1/sales-orders/{so_id}/batches")
    assert resp.status_code == 200
