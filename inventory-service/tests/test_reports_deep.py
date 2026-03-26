"""Deep reports tests — PnL, events CSV, batches CSV, serials CSV, PO CSV, movements CSV."""
import pytest
from httpx import AsyncClient


async def _seed(client: AsyncClient, suffix: str):
    p = await client.post("/api/v1/products", json={
        "name": f"Prod-{suffix}", "sku": f"RD-{suffix}", "unit_of_measure": "un",
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{suffix}", "code": f"WH-RD-{suffix}", "type": "main",
    })
    pid, wid = p.json()["id"], w.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "100", "unit_cost": "5000",
    })
    return pid, wid


@pytest.mark.asyncio
async def test_pnl_report(client: AsyncClient):
    await _seed(client, "PNL")
    resp = await client.get("/api/v1/reports/pnl")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pnl_report_with_dates(client: AsyncClient):
    await _seed(client, "PNLD")
    resp = await client.get("/api/v1/reports/pnl", params={
        "date_from": "2024-01-01", "date_to": "2027-12-31",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_events_csv(client: AsyncClient):
    resp = await client.get("/api/v1/reports/events")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_batches_csv(client: AsyncClient):
    resp = await client.get("/api/v1/reports/batches")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_serials_csv(client: AsyncClient):
    resp = await client.get("/api/v1/reports/serials")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_po_csv(client: AsyncClient):
    resp = await client.get("/api/v1/reports/purchase-orders")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_movements_csv_with_dates(client: AsyncClient):
    await _seed(client, "MVRD")
    resp = await client.get("/api/v1/reports/movements", params={
        "date_from": "2024-01-01", "date_to": "2027-12-31",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_products_csv(client: AsyncClient):
    resp = await client.get("/api/v1/reports/products")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_stock_csv(client: AsyncClient):
    resp = await client.get("/api/v1/reports/stock")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_suppliers_csv(client: AsyncClient):
    resp = await client.get("/api/v1/reports/suppliers")
    assert resp.status_code == 200
