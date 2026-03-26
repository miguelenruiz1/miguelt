"""Tests for reports, portal, health, alerts, and reorder route endpoints."""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uid() -> str:
    return str(uuid.uuid4())


async def _seed_product_warehouse(client: AsyncClient, suffix: str):
    """Create a product + warehouse + receive stock; return (product_id, warehouse_id)."""
    p = await client.post("/api/v1/products", json={
        "name": f"Prod-{suffix}", "sku": f"RR-{suffix}", "unit_of_measure": "un",
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{suffix}", "code": f"WH-RR-{suffix}", "type": "main",
    })
    pid, wid = p.json()["id"], w.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50", "unit_cost": "1000",
    })
    return pid, wid


async def _create_customer(db: AsyncSession, code: str) -> str:
    """Insert a Customer row directly and return its id."""
    from app.db.models.customer import Customer
    cid = _uid()
    customer = Customer(
        id=cid,
        tenant_id="test-tenant",
        name=f"Portal Customer {code}",
        code=code,
        is_active=True,
    )
    db.add(customer)
    await db.flush()
    return cid


# ═════════════════════════════════════════════════════════════════════════════
# Reports — CSV downloads
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_events_csv_download(client: AsyncClient):
    """GET /api/v1/reports/events returns CSV."""
    await _seed_product_warehouse(client, "EVT-CSV1")
    resp = await client.get("/api/v1/reports/events")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_events_csv_with_date_range(client: AsyncClient):
    """GET /api/v1/reports/events with date_from & date_to."""
    await _seed_product_warehouse(client, "EVT-CSV2")
    resp = await client.get("/api/v1/reports/events", params={
        "date_from": "2024-01-01", "date_to": "2027-12-31",
    })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_serials_csv_download(client: AsyncClient):
    """GET /api/v1/reports/serials returns CSV."""
    resp = await client.get("/api/v1/reports/serials")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "seriales.csv" in resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_batches_csv_download(client: AsyncClient):
    """GET /api/v1/reports/batches returns CSV."""
    resp = await client.get("/api/v1/reports/batches")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "lotes.csv" in resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_purchase_orders_csv_download(client: AsyncClient):
    """GET /api/v1/reports/purchase-orders returns CSV."""
    resp = await client.get("/api/v1/reports/purchase-orders")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "ordenes-compra.csv" in resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_purchase_orders_csv_with_dates(client: AsyncClient):
    """GET /api/v1/reports/purchase-orders with date filters."""
    resp = await client.get("/api/v1/reports/purchase-orders", params={
        "date_from": "2025-01-01", "date_to": "2027-06-30",
    })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


# ═════════════════════════════════════════════════════════════════════════════
# Reports — P&L (JSON)
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_pnl_report_full(client: AsyncClient):
    """GET /api/v1/reports/pnl returns JSON P&L."""
    await _seed_product_warehouse(client, "PNL-FULL1")
    resp = await client.get("/api/v1/reports/pnl")
    assert resp.status_code == 200
    body = resp.json()
    # P&L should be a dict with summary keys
    assert isinstance(body, dict)


@pytest.mark.asyncio
async def test_pnl_report_with_dates(client: AsyncClient):
    """GET /api/v1/reports/pnl with date range."""
    resp = await client.get("/api/v1/reports/pnl", params={
        "date_from": "2025-01-01", "date_to": "2027-12-31",
    })
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


@pytest.mark.asyncio
async def test_pnl_report_single_product(client: AsyncClient):
    """GET /api/v1/reports/pnl?product_id=xxx scopes to one product."""
    pid, _ = await _seed_product_warehouse(client, "PNL-PROD1")
    resp = await client.get("/api/v1/reports/pnl", params={"product_id": pid})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict)


@pytest.mark.asyncio
async def test_pnl_report_nonexistent_product(client: AsyncClient):
    """GET /api/v1/reports/pnl with bogus product_id still returns (empty data)."""
    fake_id = _uid()
    resp = await client.get("/api/v1/reports/pnl", params={"product_id": fake_id})
    # Service should return 200 with zeroed data (not 404)
    assert resp.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# Portal endpoints
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_portal_stock_empty(client: AsyncClient, db: AsyncSession):
    """GET /api/v1/portal/stock returns empty list when customer has no orders."""
    cid = await _create_customer(db, "PC-STK1")
    resp = await client.get("/api/v1/portal/stock", params={"customer_id": cid})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_portal_stock_missing_param(client: AsyncClient):
    """GET /api/v1/portal/stock without customer_id → 422."""
    resp = await client.get("/api/v1/portal/stock")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_portal_orders_empty(client: AsyncClient, db: AsyncSession):
    """GET /api/v1/portal/orders returns empty list for customer with no orders."""
    cid = await _create_customer(db, "PC-ORD1")
    resp = await client.get("/api/v1/portal/orders", params={"customer_id": cid})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_portal_orders_missing_param(client: AsyncClient):
    """GET /api/v1/portal/orders without customer_id → 422."""
    resp = await client.get("/api/v1/portal/orders")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_portal_order_detail_not_found(client: AsyncClient, db: AsyncSession):
    """GET /api/v1/portal/orders/{id} for non-existent order → 404."""
    cid = await _create_customer(db, "PC-DET1")
    fake_order = _uid()
    resp = await client.get(
        f"/api/v1/portal/orders/{fake_order}",
        params={"customer_id": cid},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_portal_order_detail_missing_customer(client: AsyncClient):
    """GET /api/v1/portal/orders/{id} without customer_id → 422."""
    fake_order = _uid()
    resp = await client.get(f"/api/v1/portal/orders/{fake_order}")
    assert resp.status_code == 422


# ═════════════════════════════════════════════════════════════════════════════
# Health endpoints
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /health returns 200 with status ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "inventory-service"


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    """GET /ready — accept 200 (ready) or 503 (not_ready in test env)."""
    resp = await client.get("/ready")
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert "status" in body


# ═════════════════════════════════════════════════════════════════════════════
# Alerts endpoints
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_alerts_unread_count(client: AsyncClient):
    """GET /api/v1/alerts/unread-count returns count."""
    resp = await client.get("/api/v1/alerts/unread-count")
    assert resp.status_code == 200
    body = resp.json()
    assert "count" in body
    assert isinstance(body["count"], int)
    assert body["count"] >= 0


@pytest.mark.asyncio
async def test_alert_mark_read_not_found(client: AsyncClient):
    """POST /api/v1/alerts/{id}/read with bogus id → 404."""
    fake_id = _uid()
    resp = await client.post(f"/api/v1/alerts/{fake_id}/read")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_alert_resolve_not_found(client: AsyncClient):
    """POST /api/v1/alerts/{id}/resolve with bogus id → 404."""
    fake_id = _uid()
    resp = await client.post(f"/api/v1/alerts/{fake_id}/resolve")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_alerts_list_empty(client: AsyncClient):
    """GET /api/v1/alerts returns paginated list (possibly empty)."""
    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)


# ═════════════════════════════════════════════════════════════════════════════
# Reorder endpoints
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_reorder_check_all(client: AsyncClient):
    """POST /api/v1/reorder/check triggers full reorder scan."""
    resp = await client.post("/api/v1/reorder/check")
    assert resp.status_code == 200
    body = resp.json()
    # Returns a list of created POs (may be empty)
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_reorder_check_single_product(client: AsyncClient):
    """POST /api/v1/reorder/check/{product_id} for a product with no reorder config → null."""
    pid, _ = await _seed_product_warehouse(client, "RO-SNGL1")
    resp = await client.post(f"/api/v1/reorder/check/{pid}")
    assert resp.status_code == 200
    # Product has no auto_reorder/preferred_supplier, so result is null
    assert resp.json() is None


@pytest.mark.asyncio
async def test_reorder_check_nonexistent_product(client: AsyncClient):
    """POST /api/v1/reorder/check/{product_id} with bogus id → null (no product found)."""
    fake_id = _uid()
    resp = await client.post(f"/api/v1/reorder/check/{fake_id}")
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_reorder_config(client: AsyncClient):
    """GET /api/v1/reorder/config returns reorder configuration list."""
    resp = await client.get("/api/v1/reorder/config")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
