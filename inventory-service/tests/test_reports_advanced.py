"""Advanced reports tests — CSV exports, supplier reports, audit logs, warehouses advanced."""
import pytest
from httpx import AsyncClient


async def _seed(client: AsyncClient, suffix: str):
    p = await client.post("/api/v1/products", json={
        "name": f"Prod-{suffix}", "sku": f"RPT-{suffix}", "unit_of_measure": "un",
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{suffix}", "code": f"WH-RPT-{suffix}", "type": "main",
    })
    pid, wid = p.json()["id"], w.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "100", "unit_cost": "5000",
    })
    return pid, wid


# ── CSV reports with date range ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_movements_csv_with_dates(client: AsyncClient):
    await _seed(client, "MVCSV")
    resp = await client.get("/api/v1/reports/movements", params={
        "date_from": "2024-01-01", "date_to": "2027-12-31",
    })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_products_csv_report(client: AsyncClient):
    await _seed(client, "PRDCSV")
    resp = await client.get("/api/v1/reports/products")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_stock_csv_report(client: AsyncClient):
    await _seed(client, "STKCSV")
    resp = await client.get("/api/v1/reports/stock")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_suppliers_csv_report(client: AsyncClient):
    resp = await client.get("/api/v1/reports/suppliers")
    assert resp.status_code == 200


# ── Audit log ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log(client: AsyncClient):
    # Create something to generate audit log
    await client.post("/api/v1/products", json={
        "name": "AuditProd", "sku": "AUDIT-001", "unit_of_measure": "un",
    })
    resp = await client.get("/api/v1/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_audit_log_with_filters(client: AsyncClient):
    resp = await client.get("/api/v1/audit", params={
        "resource_type": "product", "offset": 0, "limit": 10,
    })
    assert resp.status_code == 200


# ── Warehouse advanced ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_warehouse(client: AsyncClient):
    w = await client.post("/api/v1/warehouses", json={
        "name": "WH-UPD", "code": "WH-UPD-001", "type": "main",
    })
    wid = w.json()["id"]
    resp = await client.patch(f"/api/v1/warehouses/{wid}", json={"name": "Updated WH"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_warehouse(client: AsyncClient):
    w = await client.post("/api/v1/warehouses", json={
        "name": "WH-DEL", "code": "WH-DEL-001", "type": "secondary",
    })
    wid = w.json()["id"]
    resp = await client.delete(f"/api/v1/warehouses/{wid}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_get_warehouse(client: AsyncClient):
    w = await client.post("/api/v1/warehouses", json={
        "name": "WH-GET", "code": "WH-GET-001", "type": "main",
    })
    wid = w.json()["id"]
    resp = await client.get(f"/api/v1/warehouses/{wid}")
    assert resp.status_code == 200


# ── Category advanced ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_category(client: AsyncClient):
    c = await client.post("/api/v1/categories", json={"name": "CatUpd"})
    cid = c.json()["id"]
    resp = await client.patch(f"/api/v1/categories/{cid}", json={"name": "Updated Cat"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_category(client: AsyncClient):
    c = await client.post("/api/v1/categories", json={"name": "CatDel"})
    cid = c.json()["id"]
    resp = await client.delete(f"/api/v1/categories/{cid}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_get_category(client: AsyncClient):
    c = await client.post("/api/v1/categories", json={"name": "CatGet"})
    cid = c.json()["id"]
    resp = await client.get(f"/api/v1/categories/{cid}")
    assert resp.status_code == 200


# ── Product search ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_product_search(client: AsyncClient):
    await client.post("/api/v1/products", json={
        "name": "Searchable Widget", "sku": "SEARCH-001", "unit_of_measure": "un",
    })
    resp = await client.get("/api/v1/products", params={"q": "Searchable"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_product_filter_by_category(client: AsyncClient):
    c = await client.post("/api/v1/categories", json={"name": "FilterCat"})
    cid = c.json()["id"]
    await client.post("/api/v1/products", json={
        "name": "CatProd", "sku": "CATFLT-001", "unit_of_measure": "un",
        "category_id": cid,
    })
    resp = await client.get("/api/v1/products", params={"category_id": cid})
    assert resp.status_code == 200
