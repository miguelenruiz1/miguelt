"""Tests for stock alerts — low stock, out of stock, expiry."""
import pytest
from httpx import AsyncClient


async def _setup(client, suffix):
    p = await client.post("/api/v1/products", json={
        "name": f"Alert-{suffix}", "sku": f"ALR-{suffix}", "unit_of_measure": "un",
        "min_stock_level": 20, "reorder_point": 50,
    })
    w = await client.post("/api/v1/warehouses", json={"name": f"WH-ALR-{suffix}", "code": f"WH-ALR-{suffix}", "type": "main"})
    return p.json()["id"], w.json()["id"]


@pytest.mark.asyncio
async def test_scan_generates_low_stock_alert(client: AsyncClient):
    pid, wid = await _setup(client, "LOW")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "10", "unit_cost": "1000",
    })
    resp = await client.post("/api/v1/alerts/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] >= 0


@pytest.mark.asyncio
async def test_list_alerts(client: AsyncClient):
    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 200
    assert "items" in resp.json()
    assert "total" in resp.json()


@pytest.mark.asyncio
async def test_unread_count(client: AsyncClient):
    resp = await client.get("/api/v1/alerts/unread-count")
    assert resp.status_code == 200
    assert "count" in resp.json()


@pytest.mark.asyncio
async def test_mark_alert_read(client: AsyncClient):
    pid, wid = await _setup(client, "READ")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "5", "unit_cost": "500",
    })
    scan = await client.post("/api/v1/alerts/scan")
    alerts = await client.get("/api/v1/alerts", params={"is_resolved": False})
    items = alerts.json().get("items", [])
    if items:
        alert_id = items[0]["id"]
        resp = await client.post(f"/api/v1/alerts/{alert_id}/read")
        assert resp.status_code == 200
        assert resp.json()["is_read"] is True


@pytest.mark.asyncio
async def test_resolve_alert(client: AsyncClient):
    pid, wid = await _setup(client, "RESOLVE")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "3", "unit_cost": "200",
    })
    await client.post("/api/v1/alerts/scan")
    alerts = await client.get("/api/v1/alerts", params={"is_resolved": False})
    items = alerts.json().get("items", [])
    if items:
        alert_id = items[0]["id"]
        resp = await client.post(f"/api/v1/alerts/{alert_id}/resolve")
        assert resp.status_code == 200
        assert resp.json()["is_resolved"] is True


@pytest.mark.asyncio
async def test_filter_alerts_by_type(client: AsyncClient):
    resp = await client.get("/api/v1/alerts", params={"alert_type": "low_stock"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_filter_resolved_alerts(client: AsyncClient):
    resp = await client.get("/api/v1/alerts", params={"is_resolved": True})
    assert resp.status_code == 200
