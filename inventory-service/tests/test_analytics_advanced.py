"""Tests for analytics — overview, occupation, ABC, EOQ, stock-policy, storage-valuation, committed-stock."""
import pytest
from httpx import AsyncClient


async def _seed_data(client: AsyncClient, suffix: str):
    """Create product + warehouse + stock for analytics."""
    p = await client.post("/api/v1/products", json={
        "name": f"Prod-{suffix}", "sku": f"AN-{suffix}", "unit_of_measure": "un",
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{suffix}", "code": f"WH-AN-{suffix}", "type": "main",
        "cost_per_sqm": 5.0, "total_area_sqm": 100.0,
    })
    pid, wid = p.json()["id"], w.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "100", "unit_cost": "5000",
    })
    # Create a sale movement for analytics
    await client.post("/api/v1/stock/issue", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "20",
    })
    return pid, wid


@pytest.mark.asyncio
async def test_analytics_overview(client: AsyncClient):
    await _seed_data(client, "OVW")
    resp = await client.get("/api/v1/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_skus" in data
    assert "total_value" in data
    assert "movement_trend" in data
    assert "movements_by_type" in data


@pytest.mark.asyncio
async def test_analytics_occupation(client: AsyncClient):
    await _seed_data(client, "OCC")
    resp = await client.get("/api/v1/analytics/occupation")
    assert resp.status_code == 200
    data = resp.json()
    assert "occupation_pct" in data or "by_warehouse" in data or "stale_stock" in data


@pytest.mark.asyncio
async def test_analytics_occupation_per_warehouse(client: AsyncClient):
    _, wid = await _seed_data(client, "OCCWH")
    resp = await client.get("/api/v1/analytics/occupation", params={"warehouse_id": wid})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_abc(client: AsyncClient):
    await _seed_data(client, "ABC")
    resp = await client.get("/api/v1/analytics/abc")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data or "items" in data or "A" in data


@pytest.mark.asyncio
async def test_analytics_abc_custom_months(client: AsyncClient):
    await _seed_data(client, "ABC6")
    resp = await client.get("/api/v1/analytics/abc", params={"months": 6})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_eoq(client: AsyncClient):
    await _seed_data(client, "EOQ")
    resp = await client.get("/api/v1/analytics/eoq", params={
        "ordering_cost": 50, "holding_cost_pct": 25,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data or "products" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_analytics_stock_policy(client: AsyncClient):
    # Create a product type with rotation target
    pt = await client.post("/api/v1/config/product-types", json={
        "name": "Rotatable", "rotation_target_months": 6,
    })
    pt_id = pt.json()["id"]
    p = await client.post("/api/v1/products", json={
        "name": "Rot-Prod", "sku": "AN-ROTPOL", "unit_of_measure": "un",
        "product_type_id": pt_id,
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": "WH-ROTPOL", "code": "WH-AN-ROTPOL", "type": "main",
    })
    pid, wid = p.json()["id"], w.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "100", "unit_cost": "3000",
    })
    resp = await client.get("/api/v1/analytics/stock-policy")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_storage_valuation(client: AsyncClient):
    await _seed_data(client, "STVAL")
    resp = await client.get("/api/v1/analytics/storage-valuation")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_monthly_cost" in data or "warehouses" in data or "total_stock_value" in data


@pytest.mark.asyncio
async def test_analytics_committed_stock(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/committed-stock")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_reserved_qty" in data or "products_with_reservations" in data
