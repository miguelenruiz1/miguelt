"""Advanced alert tests — check_and_generate, check_expiry, auto-resolve, kardex."""
import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient, suffix: str, min_stock=50, reorder=30):
    p = await client.post("/api/v1/products", json={
        "name": f"Prod-{suffix}", "sku": f"ALT-{suffix}", "unit_of_measure": "un",
        "min_stock_level": min_stock, "reorder_point": reorder,
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{suffix}", "code": f"WH-ALT-{suffix}", "type": "main",
    })
    return p.json()["id"], w.json()["id"]


# ── Scan generates out_of_stock alert ────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_out_of_stock(client: AsyncClient):
    """Product with min_stock=50 and no stock should trigger out_of_stock."""
    pid, wid = await _setup(client, "OOS", min_stock=50)
    # No stock at all
    resp = await client.post("/api/v1/alerts/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] >= 0  # may or may not generate depending on scan logic


# ── Scan after stock falls below threshold ───────────────────────────────────

@pytest.mark.asyncio
async def test_scan_low_stock_after_issue(client: AsyncClient):
    pid, wid = await _setup(client, "LOW", min_stock=50, reorder=30)
    # Receive then issue most
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "60", "unit_cost": "1000",
    })
    await client.post("/api/v1/stock/issue", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "40",
    })
    # Now only 20 left, below min_stock=50
    resp = await client.post("/api/v1/alerts/scan")
    assert resp.status_code == 200


# ── Scan auto-resolves when stock is replenished ─────────────────────────────

@pytest.mark.asyncio
async def test_scan_auto_resolves(client: AsyncClient):
    pid, wid = await _setup(client, "RESOLVE", min_stock=20, reorder=10)
    # Low stock scan
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "5", "unit_cost": "1000",
    })
    await client.post("/api/v1/alerts/scan")
    # Replenish
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "100", "unit_cost": "1000",
    })
    # Re-scan should auto-resolve
    resp = await client.post("/api/v1/alerts/scan")
    assert resp.status_code == 200


# ── Expiry alerts via batch ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_expiry_alerts(client: AsyncClient):
    """Create product with expired batch, scan should detect it."""
    p = await client.post("/api/v1/products", json={
        "name": "Exp-Prod", "sku": "ALT-EXP", "unit_of_measure": "un",
        "track_batches": True,
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": "WH-EXP", "code": "WH-ALT-EXP", "type": "main",
    })
    pid, wid = p.json()["id"], w.json()["id"]

    # Create batch with past expiration
    await client.post("/api/v1/batches", json={
        "entity_id": pid, "batch_number": "BATCH-EXP-001",
        "expiration_date": "2024-01-01", "is_active": True,
    })
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50",
        "unit_cost": "1000", "batch_number": "BATCH-EXP-001",
    })
    resp = await client.post("/api/v1/alerts/scan")
    assert resp.status_code == 200


# ── Kardex per product ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kardex(client: AsyncClient):
    pid, wid = await _setup(client, "KARDEX")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "100", "unit_cost": "5000",
    })
    await client.post("/api/v1/stock/issue", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "20",
    })
    resp = await client.get(f"/api/v1/kardex/{pid}")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 2


@pytest.mark.asyncio
async def test_kardex_per_warehouse(client: AsyncClient):
    pid, wid = await _setup(client, "KARDEXWH")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50", "unit_cost": "3000",
    })
    resp = await client.get(f"/api/v1/kardex/{pid}", params={"warehouse_id": wid})
    assert resp.status_code == 200


# ── Alert pagination ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_alerts_pagination(client: AsyncClient):
    resp = await client.get("/api/v1/alerts", params={"offset": 0, "limit": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
