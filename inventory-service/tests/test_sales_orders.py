"""Tests for sales order lifecycle — draft, confirm, pick, ship, deliver."""
import pytest
from httpx import AsyncClient


async def _setup_with_stock(client: AsyncClient, suffix: str, qty: int = 100):
    p = await client.post("/api/v1/products", json={"name": f"Prod-{suffix}", "sku": f"SO-{suffix}", "unit_of_measure": "un"})
    w = await client.post("/api/v1/warehouses", json={"name": f"WH-{suffix}", "code": f"WH-SO-{suffix}", "type": "main"})
    c = await client.post("/api/v1/partners", json={"name": f"Client-{suffix}", "code": f"CLI-{suffix}", "is_customer": True, "is_active": True})
    pid, wid, cid = p.json()["id"], w.json()["id"], c.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": str(qty), "unit_cost": "10000",
    })
    return pid, wid, cid


@pytest.mark.asyncio
async def test_create_sales_order(client: AsyncClient):
    pid, wid, cid = await _setup_with_stock(client, "CREATE")
    resp = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 10, "unit_price": 15000}],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert len(data["lines"]) == 1


@pytest.mark.asyncio
async def test_so_confirm_reserves_stock(client: AsyncClient):
    pid, wid, cid = await _setup_with_stock(client, "CONFIRM")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 20, "unit_price": 12000}],
    })
    so_id = so.json()["id"]
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    assert resp.status_code == 200
    result = resp.json()
    assert result["order"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_so_backorder_split(client: AsyncClient):
    pid, wid, cid = await _setup_with_stock(client, "BACKORDER", qty=50)
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 80, "unit_price": 10000}],
    })
    so_id = so.json()["id"]
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    assert resp.status_code == 200
    result = resp.json()
    assert result["split_preview"]["has_backorder"] is True
    assert result["backorder"] is not None


@pytest.mark.asyncio
async def test_so_full_lifecycle(client: AsyncClient):
    pid, wid, cid = await _setup_with_stock(client, "LIFECYCLE", qty=200)
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 30, "unit_price": 15000}],
    })
    so_id = so.json()["id"]
    # Confirm
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    assert resp.status_code == 200
    # Pick
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/pick")
    assert resp.status_code == 200
    assert resp.json()["status"] == "picking"
    # Ship
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/ship")
    assert resp.status_code == 200
    assert resp.json()["status"] == "shipped"
    # Deliver
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/deliver")
    assert resp.status_code == 200
    assert resp.json()["status"] == "delivered"


@pytest.mark.asyncio
async def test_so_cancel_releases_reservation(client: AsyncClient):
    pid, wid, cid = await _setup_with_stock(client, "CANCEL")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 25, "unit_price": 8000}],
    })
    so_id = so.json()["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    resp = await client.post(f"/api/v1/sales-orders/{so_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_so_stock_check(client: AsyncClient):
    pid, wid, cid = await _setup_with_stock(client, "STKCHK")
    so = await client.post("/api/v1/sales-orders", json={
        "customer_id": cid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 10, "unit_price": 5000}],
    })
    so_id = so.json()["id"]
    await client.post(f"/api/v1/sales-orders/{so_id}/confirm")
    resp = await client.get(f"/api/v1/sales-orders/{so_id}/stock-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready_to_ship"] is True
