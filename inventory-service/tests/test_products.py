"""Tests for product CRUD endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_product(client: AsyncClient):
    resp = await client.post("/api/v1/products", json={
        "name": "Detergente 1L", "sku": "DET-001", "unit_of_measure": "un",
        "min_stock_level": 10, "reorder_point": 20, "reorder_quantity": 50,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["sku"] == "DET-001"
    assert data["name"] == "Detergente 1L"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_product_duplicate_sku(client: AsyncClient):
    await client.post("/api/v1/products", json={"name": "A", "sku": "DUP-001", "unit_of_measure": "un"})
    resp = await client.post("/api/v1/products", json={"name": "B", "sku": "DUP-001", "unit_of_measure": "un"})
    assert resp.status_code in (409, 422, 500)


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient):
    await client.post("/api/v1/products", json={"name": "Prod1", "sku": "LIST-001", "unit_of_measure": "un"})
    await client.post("/api/v1/products", json={"name": "Prod2", "sku": "LIST-002", "unit_of_measure": "un"})
    resp = await client.get("/api/v1/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_get_product_by_id(client: AsyncClient):
    create = await client.post("/api/v1/products", json={"name": "GetMe", "sku": "GET-001", "unit_of_measure": "un"})
    pid = create.json()["id"]
    resp = await client.get(f"/api/v1/products/{pid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == pid


@pytest.mark.asyncio
async def test_update_product(client: AsyncClient):
    create = await client.post("/api/v1/products", json={"name": "Old", "sku": "UPD-001", "unit_of_measure": "un"})
    pid = create.json()["id"]
    resp = await client.patch(f"/api/v1/products/{pid}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient):
    create = await client.post("/api/v1/products", json={"name": "DelMe", "sku": "DEL-001", "unit_of_measure": "un"})
    pid = create.json()["id"]
    resp = await client.delete(f"/api/v1/products/{pid}")
    assert resp.status_code in (200, 204)


@pytest.mark.asyncio
async def test_search_products(client: AsyncClient):
    await client.post("/api/v1/products", json={"name": "Jabon Liquido", "sku": "SEARCH-001", "unit_of_measure": "un"})
    resp = await client.get("/api/v1/products", params={"search": "Jabon"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_product_with_weight(client: AsyncClient):
    resp = await client.post("/api/v1/products", json={
        "name": "Cemento 50kg", "sku": "CEM-001", "unit_of_measure": "bolsa",
        "weight_per_unit": 50.0,
    })
    assert resp.status_code == 201
