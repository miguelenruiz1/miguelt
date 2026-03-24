"""Tests for purchase order lifecycle."""
import uuid
import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient, db, suffix: str = "PO"):
    """Create product, warehouse, and supplier (directly in DB since PO FK references suppliers table)."""
    p = await client.post("/api/v1/products", json={"name": f"Prod-{suffix}", "sku": f"PO-{suffix}", "unit_of_measure": "un"})
    w = await client.post("/api/v1/warehouses", json={"name": f"WH-{suffix}", "code": f"WH-PO-{suffix}", "type": "main"})
    pid, wid = p.json()["id"], w.json()["id"]

    # Create supplier directly in DB (PO FK references suppliers table)
    from app.db.models.supplier import Supplier
    sid = str(uuid.uuid4())
    supplier = Supplier(id=sid, tenant_id="test-tenant", name=f"Supplier-{suffix}", code=f"SUP-{suffix}", is_active=True)
    db.add(supplier)
    await db.flush()
    return pid, wid, sid


@pytest.mark.asyncio
async def test_create_purchase_order(client: AsyncClient, db):
    pid, wid, sid = await _setup(client, db, "CREATE")
    resp = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 100, "unit_cost": 5000}],
    })
    assert resp.status_code == 201, f"PO create failed: {resp.json()}"
    data = resp.json()
    assert data["status"] == "draft"
    assert len(data["lines"]) == 1


@pytest.mark.asyncio
async def test_po_lifecycle_draft_to_confirmed(client: AsyncClient, db):
    pid, wid, sid = await _setup(client, db, "LIFE")
    po = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 50, "unit_cost": 3000}],
    })
    po_id = po.json()["id"]
    resp = await client.post(f"/api/v1/purchase-orders/{po_id}/send")
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"
    resp = await client.post(f"/api/v1/purchase-orders/{po_id}/confirm")
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_po_receive(client: AsyncClient, db):
    pid, wid, sid = await _setup(client, db, "RECV")
    po = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 100, "unit_cost": 2000}],
    })
    po_id = po.json()["id"]
    line_id = po.json()["lines"][0]["id"]
    await client.post(f"/api/v1/purchase-orders/{po_id}/send")
    await client.post(f"/api/v1/purchase-orders/{po_id}/confirm")
    resp = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 100}],
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"


@pytest.mark.asyncio
async def test_po_partial_receive(client: AsyncClient, db):
    pid, wid, sid = await _setup(client, db, "PARTIAL")
    po = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 100, "unit_cost": 1500}],
    })
    po_id = po.json()["id"]
    line_id = po.json()["lines"][0]["id"]
    await client.post(f"/api/v1/purchase-orders/{po_id}/send")
    await client.post(f"/api/v1/purchase-orders/{po_id}/confirm")
    resp = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 60}],
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "partial"


@pytest.mark.asyncio
async def test_po_cancel(client: AsyncClient, db):
    pid, wid, sid = await _setup(client, db, "CANCEL")
    po = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sid, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 20, "unit_cost": 1000}],
    })
    po_id = po.json()["id"]
    resp = await client.post(f"/api/v1/purchase-orders/{po_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"
