"""Tests for categories, product types, and configuration endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_category(client: AsyncClient):
    resp = await client.post("/api/v1/categories", json={"name": "Limpieza", "slug": "limpieza"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Limpieza"


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient):
    await client.post("/api/v1/categories", json={"name": "Electrico", "slug": "electrico"})
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_create_product_type(client: AsyncClient):
    resp = await client.post("/api/v1/config/product-types", json={
        "name": "Materia Prima", "code": "MP", "color": "#3b82f6",
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "Materia Prima"


@pytest.mark.asyncio
async def test_create_warehouse_type(client: AsyncClient):
    resp = await client.post("/api/v1/config/warehouse-types", json={
        "name": "Rack Selectivo", "code": "RACK-SEL",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_movement_type(client: AsyncClient):
    resp = await client.post("/api/v1/config/movement-types", json={
        "name": "Ajuste por Inventario", "code": "ADJ-INV", "direction": "both",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
