"""Tests for warehouse and location endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_warehouse(client: AsyncClient):
    resp = await client.post("/api/v1/warehouses", json={
        "name": "Bodega Principal", "code": "MAIN-001", "type": "main",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Bodega Principal"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_warehouse_with_capacity(client: AsyncClient):
    resp = await client.post("/api/v1/warehouses", json={
        "name": "Bodega Fria", "code": "COLD-001", "type": "secondary",
        "max_stock_capacity": 5000,
    })
    assert resp.status_code == 201
    assert resp.json()["max_stock_capacity"] == 5000


@pytest.mark.asyncio
async def test_list_warehouses(client: AsyncClient):
    await client.post("/api/v1/warehouses", json={"name": "WH-A", "code": "WH-LIST-A", "type": "main"})
    resp = await client.get("/api/v1/warehouses")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_create_location(client: AsyncClient):
    wh = await client.post("/api/v1/warehouses", json={"name": "WH-Loc", "code": "WH-LOC-001", "type": "main"})
    wh_id = wh.json()["id"]
    resp = await client.post("/api/v1/config/locations", json={
        "warehouse_id": wh_id, "name": "Rack A - Nivel 1", "code": "A-01-01",
        "location_type": "bin", "max_weight_kg": 500, "max_capacity": 100,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "A-01-01"
    assert data["max_weight_kg"] == 500
    assert data["max_capacity"] == 100


@pytest.mark.asyncio
async def test_create_location_hierarchy(client: AsyncClient):
    wh = await client.post("/api/v1/warehouses", json={"name": "WH-Hier", "code": "WH-HIER-001", "type": "main"})
    wh_id = wh.json()["id"]
    parent = await client.post("/api/v1/config/locations", json={
        "warehouse_id": wh_id, "name": "Zona Racks", "code": "ZONE-RACK", "location_type": "zone",
    })
    parent_id = parent.json()["id"]
    child = await client.post("/api/v1/config/locations", json={
        "warehouse_id": wh_id, "name": "Rack A", "code": "RACK-A",
        "parent_location_id": parent_id, "location_type": "rack",
    })
    assert child.status_code == 201
    assert child.json()["parent_location_id"] == parent_id


@pytest.mark.asyncio
async def test_create_blocked_location(client: AsyncClient):
    wh = await client.post("/api/v1/warehouses", json={"name": "WH-Block", "code": "WH-BLK-001", "type": "main"})
    wh_id = wh.json()["id"]
    resp = await client.post("/api/v1/config/locations", json={
        "warehouse_id": wh_id, "name": "Zona Cuarentena", "code": "QUARANTINE",
        "blocked_inbound": False, "blocked_outbound": True, "block_reason": "QC pending",
    })
    assert resp.status_code == 201
    assert resp.json()["blocked_outbound"] is True
    assert resp.json()["block_reason"] == "QC pending"


@pytest.mark.asyncio
async def test_bulk_create_locations(client: AsyncClient):
    wh = await client.post("/api/v1/warehouses", json={"name": "WH-Bulk", "code": "WH-BULK-001", "type": "main"})
    wh_id = wh.json()["id"]
    locations = [
        {"warehouse_id": wh_id, "name": f"Bin {i}", "code": f"BIN-{i:03d}", "location_type": "bin"}
        for i in range(1, 11)
    ]
    resp = await client.post("/api/v1/config/locations/bulk", json=locations)
    assert resp.status_code == 201
    assert len(resp.json()) == 10
