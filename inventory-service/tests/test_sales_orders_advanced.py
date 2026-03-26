"""Advanced sales order tests — ship, deliver, return, discount, approval, reservations, remission."""
import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient, suffix: str, qty: int = 200):
    p = await client.post("/api/v1/products", json={
        "name": f"Prod-{suffix}", "sku": f"SOA-{suffix}", "unit_of_measure": "un",
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{suffix}", "code": f"WH-SOA-{suffix}", "type": "main",
    })
    c = await client.post("/api/v1/partners", json={
        "name": f"Client-{suffix}", "code": f"CLIA-{suffix}", "is_customer": True,
    })
    pid, wid, cid = p.json()["id"], w.json()["id"], c.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": str(qty), "unit_cost": "10000",
    })
    return pid, wid, cid


async def _create_and_confirm(client, pid, wid, cid, qty=10, price=15000):
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": qty, "unit_price": price}],
    })
    so_id = so.json()["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    return so_id


# ── Ship with line_shipments ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ship_with_line_shipments(client: AsyncClient):
    pid, wid, cid = await _setup(client, "SHIP-LINES")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 20, "unit_price": 10000}],
    })
    so_id = so.json()["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    await client.post(f"/api/v1/sales-orders/{so_id}/pick")

    lines = (await client.get(f"/api/v1/sales-orders/{so_id}")).json()["lines"]
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/ship", json={
        "line_shipments": [{"line_id": lines[0]["id"], "qty_shipped": 20}],
        "shipping_info": {"carrier": "FedEx", "tracking_number": "TRACK-123"},
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "shipped"


# ── Deliver after ship ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deliver_deducts_stock(client: AsyncClient):
    pid, wid, cid = await _setup(client, "DELIVER")
    so_id = await _create_and_confirm(client, pid, wid, cid, qty=15)
    await client.post(f"/api/v1/sales-orders/{so_id}/pick")
    await client.post(f"/api/v1/sales-orders/{so_id}/ship")
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/deliver")
    assert resp.status_code == 200
    assert resp.json()["status"] == "delivered"

    # Verify stock reduced
    avail = await client.get(f"/api/v1/stock/availability/{pid}")
    data = avail.json()
    on_hand = data.get("on_hand", data.get("qty_on_hand", 0))
    assert on_hand == 200 - 15


# ── Return order ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_return_order(client: AsyncClient):
    pid, wid, cid = await _setup(client, "RETURN")
    so_id = await _create_and_confirm(client, pid, wid, cid, qty=10)
    await client.post(f"/api/v1/sales-orders/{so_id}/pick")
    await client.post(f"/api/v1/sales-orders/{so_id}/ship")
    await client.post(f"/api/v1/sales-orders/{so_id}/deliver")
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/return")
    assert resp.status_code == 200
    assert resp.json()["status"] == "returned"


# ── Cancel draft ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_draft_order(client: AsyncClient):
    pid, wid, cid = await _setup(client, "CDRAFT")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 5, "unit_price": 10000}],
    })
    so_id = so.json()["id"]
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"


# ── Update sales order ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_sales_order(client: AsyncClient):
    pid, wid, cid = await _setup(client, "UPDATE")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 5, "unit_price": 8000}],
    })
    so_id = so.json()["id"]
    resp = await client.patch(f"/api/v1/sales-orders/{so_id}", json={
        "notes": "Updated notes",
    })
    assert resp.status_code == 200


# ── Delete draft SO ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_draft_so(client: AsyncClient):
    pid, wid, cid = await _setup(client, "DELETE")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 3, "unit_price": 5000}],
    })
    so_id = so.json()["id"]
    resp = await client.delete(f"/api/v1/sales-orders/{so_id}")
    assert resp.status_code == 204


# ── Summary endpoint ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sales_summary(client: AsyncClient):
    resp = await client.get("/api/v1/sales-orders/summary")
    assert resp.status_code == 200


# ── List sales orders with filters ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sales_orders_with_filters(client: AsyncClient):
    pid, wid, cid = await _setup(client, "LISTFILT")
    await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 2, "unit_price": 5000}],
    })
    resp = await client.get("/api/v1/sales-orders", params={"status": "draft", "customer_id": cid})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ── Reservations endpoint ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_so_reservations(client: AsyncClient):
    pid, wid, cid = await _setup(client, "RESERV")
    so_id = await _create_and_confirm(client, pid, wid, cid)
    resp = await client.get(f"/api/v1/sales-orders/{so_id}/reservations")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── Discount update ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_discount(client: AsyncClient):
    pid, wid, cid = await _setup(client, "DISC")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 10, "unit_price": 10000}],
    })
    so_id = so.json()["id"]
    resp = await client.patch(f"/api/v1/sales-orders/{so_id}/discount", json={
        "discount_pct": 10.0, "discount_reason": "Promo",
    })
    assert resp.status_code == 200
    assert resp.json()["discount_pct"] == 10.0


# ── Remission (shipped order) ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_remission(client: AsyncClient):
    pid, wid, cid = await _setup(client, "REMIS")
    so_id = await _create_and_confirm(client, pid, wid, cid, qty=5)
    await client.post(f"/api/v1/sales-orders/{so_id}/pick")
    await client.post(f"/api/v1/sales-orders/{so_id}/ship")
    resp = await client.get(f"/api/v1/sales-orders/{so_id}/remission")
    assert resp.status_code == 200
    data = resp.json()
    assert "remission_number" in data or "lines" in data


# ── Backorder list ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_backorders_list(client: AsyncClient):
    pid, wid, cid = await _setup(client, "BOLIST", qty=30)
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 50, "unit_price": 10000}],
    })
    so_id = so.json()["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    resp = await client.get(f"/api/v1/sales-orders/{so_id}/backorders")
    assert resp.status_code == 200


# ── Line warehouse update ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_line_warehouse(client: AsyncClient):
    pid, wid, cid = await _setup(client, "LINEWH")
    w2 = await client.post("/api/v1/warehouses", json={"name": "WH-ALT", "code": "WH-ALT-SO", "type": "secondary"})
    wid2 = w2.json()["id"]
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 5, "unit_price": 5000}],
    })
    so_data = so.json()
    so_id = so_data["id"]
    line_id = so_data["lines"][0]["id"]
    resp = await client.patch(f"/api/v1/sales-orders/{so_id}/lines/{line_id}/warehouse", json={
        "warehouse_id": wid2,
    })
    assert resp.status_code == 200
