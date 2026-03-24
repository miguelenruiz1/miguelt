"""Tests for stock operations — receive, issue, transfer, adjust, waste, return."""
import pytest
from httpx import AsyncClient


async def _setup_product_and_warehouse(client: AsyncClient, sku: str = "STK-001"):
    """Helper: create product + warehouse, return (product_id, warehouse_id)."""
    p = await client.post("/api/v1/products", json={"name": f"Prod-{sku}", "sku": sku, "unit_of_measure": "un"})
    w = await client.post("/api/v1/warehouses", json={"name": f"WH-{sku}", "code": f"WH-{sku}", "type": "main"})
    return p.json()["id"], w.json()["id"]


@pytest.mark.asyncio
async def test_receive_stock(client: AsyncClient):
    pid, wid = await _setup_product_and_warehouse(client, "RCV-001")
    resp = await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "100", "unit_cost": "5000",
        "reference": "PO-TEST-001",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["movement_type"] == "purchase"
    assert float(data["quantity"]) == 100


@pytest.mark.asyncio
async def test_receive_requires_cost(client: AsyncClient):
    pid, wid = await _setup_product_and_warehouse(client, "RCV-002")
    resp = await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50",
    })
    assert resp.status_code in (422, 400, 500)


@pytest.mark.asyncio
async def test_issue_stock(client: AsyncClient):
    pid, wid = await _setup_product_and_warehouse(client, "ISS-001")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "100", "unit_cost": "5000",
    })
    resp = await client.post("/api/v1/stock/issue", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "30", "reference": "SO-TEST-001",
    })
    assert resp.status_code == 201
    assert resp.json()["movement_type"] == "sale"


@pytest.mark.asyncio
async def test_issue_insufficient_stock(client: AsyncClient):
    pid, wid = await _setup_product_and_warehouse(client, "ISS-002")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "10", "unit_cost": "1000",
    })
    resp = await client.post("/api/v1/stock/issue", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50",
    })
    assert resp.status_code in (422, 400, 500)


@pytest.mark.asyncio
async def test_transfer_stock(client: AsyncClient):
    pid, wid1 = await _setup_product_and_warehouse(client, "TRF-001")
    w2 = await client.post("/api/v1/warehouses", json={"name": "WH-TRF-DST", "code": "WH-TRF-DST", "type": "secondary"})
    wid2 = w2.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid1, "quantity": "100", "unit_cost": "5000",
    })
    resp = await client.post("/api/v1/stock/transfer", json={
        "product_id": pid, "from_warehouse_id": wid1, "to_warehouse_id": wid2, "quantity": "40",
    })
    assert resp.status_code == 201
    assert resp.json()["movement_type"] == "transfer"


@pytest.mark.asyncio
async def test_adjust_stock(client: AsyncClient):
    pid, wid = await _setup_product_and_warehouse(client, "ADJ-001")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "100", "unit_cost": "3000",
    })
    resp = await client.post("/api/v1/stock/adjust", json={
        "product_id": pid, "warehouse_id": wid, "new_qty": "95", "reason": "Cycle count variance",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_waste_stock(client: AsyncClient):
    pid, wid = await _setup_product_and_warehouse(client, "WST-001")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50", "unit_cost": "2000",
    })
    resp = await client.post("/api/v1/stock/waste", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "5", "reason": "Damaged in transit",
    })
    assert resp.status_code == 201
    assert resp.json()["movement_type"] == "waste"


@pytest.mark.asyncio
async def test_return_stock(client: AsyncClient):
    pid, wid = await _setup_product_and_warehouse(client, "RET-001")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50", "unit_cost": "4000",
    })
    resp = await client.post("/api/v1/stock/return", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "3", "reference": "Customer return",
    })
    assert resp.status_code == 201
    assert resp.json()["movement_type"] == "return"


@pytest.mark.asyncio
async def test_stock_levels_query(client: AsyncClient):
    pid, wid = await _setup_product_and_warehouse(client, "LVL-001")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "200", "unit_cost": "1500",
    })
    resp = await client.get("/api/v1/stock", params={"product_id": pid, "warehouse_id": wid})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert float(items[0]["qty_on_hand"]) == 200


@pytest.mark.asyncio
async def test_stock_availability(client: AsyncClient):
    pid, wid = await _setup_product_and_warehouse(client, "AVAIL-001")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "80", "unit_cost": "1000",
    })
    resp = await client.get(f"/api/v1/stock/availability/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    # Field may be on_hand or qty_on_hand
    assert data.get("on_hand", data.get("qty_on_hand", 0)) == 80
