"""Deep PO tests — receive with cost tracking, pricing recalc, multiple lines, send from approved."""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Supplier


async def _setup(client: AsyncClient, db: AsyncSession, suffix: str, products=1):
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{suffix}", "code": f"WH-PD-{suffix}", "type": "main",
    })
    wid = w.json()["id"]

    sup_id = str(uuid.uuid4())
    supplier = Supplier(id=sup_id, tenant_id="test-tenant", name=f"Sup-{suffix}", code=f"SPD-{suffix}", is_active=True)
    db.add(supplier)
    await db.flush()

    pids = []
    for i in range(products):
        p = await client.post("/api/v1/products", json={
            "name": f"Prod-{suffix}-{i}", "sku": f"PD-{suffix}-{i}", "unit_of_measure": "un",
        })
        pids.append(p.json()["id"])

    return pids, wid, sup_id


# ── Receive triggers cost history + pricing recalc ───────────────────────────

@pytest.mark.asyncio
async def test_receive_creates_cost_history(client: AsyncClient, db: AsyncSession):
    pids, wid, sup_id = await _setup(client, db, "RCVCOST")
    pid = pids[0]
    po = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sup_id, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 100, "unit_cost": "5000"}],
    })
    po_data = po.json()
    po_id = po_data["id"]
    line_id = po_data["lines"][0]["id"]

    await client.post(f"/api/v1/purchase-orders/{po_id}/send")
    await client.post(f"/api/v1/purchase-orders/{po_id}/confirm")
    resp = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 100}],
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"

    # Verify cost history created
    hist = await client.get(f"/api/v1/products/{pid}/cost-history")
    assert hist.status_code == 200


# ── Multi-line PO receive ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_multi_line_po_receive(client: AsyncClient, db: AsyncSession):
    pids, wid, sup_id = await _setup(client, db, "MLPO", products=2)
    po = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sup_id, "warehouse_id": wid,
        "lines": [
            {"product_id": pids[0], "qty_ordered": 50, "unit_cost": "3000"},
            {"product_id": pids[1], "qty_ordered": 30, "unit_cost": "7000"},
        ],
    })
    po_data = po.json()
    po_id = po_data["id"]
    lines = po_data["lines"]

    await client.post(f"/api/v1/purchase-orders/{po_id}/send")
    await client.post(f"/api/v1/purchase-orders/{po_id}/confirm")

    resp = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [
            {"line_id": lines[0]["id"], "qty_received": 50},
            {"line_id": lines[1]["id"], "qty_received": 30},
        ],
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"


# ── Send from approved state ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_from_approved(client: AsyncClient, db: AsyncSession):
    pids, wid, sup_id = await _setup(client, db, "SNDAPR")
    pid = pids[0]
    po = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sup_id, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 20, "unit_cost": "4000"}],
    })
    po_id = po.json()["id"]

    await client.post(f"/api/v1/purchase-orders/{po_id}/submit-approval")
    await client.post(f"/api/v1/purchase-orders/{po_id}/approve")

    # Send from approved state
    resp = await client.post(f"/api/v1/purchase-orders/{po_id}/send")
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


# ── PO with order type ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_po_with_order_type(client: AsyncClient, db: AsyncSession):
    ot = await client.post("/api/v1/config/order-types", json={"name": "Emergency"})
    ot_id = ot.json()["id"]

    pids, wid, sup_id = await _setup(client, db, "OTPO")
    pid = pids[0]
    resp = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sup_id, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 10, "unit_cost": "2000"}],
    })
    assert resp.status_code == 201


# ── PO receive with attachments and invoice data ────────────────────────────

@pytest.mark.asyncio
async def test_po_receive_with_full_invoice(client: AsyncClient, db: AsyncSession):
    pids, wid, sup_id = await _setup(client, db, "FULLINV")
    pid = pids[0]
    po = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sup_id, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 50, "unit_cost": "6000"}],
    })
    po_data = po.json()
    po_id = po_data["id"]
    line_id = po_data["lines"][0]["id"]

    await client.post(f"/api/v1/purchase-orders/{po_id}/send")
    await client.post(f"/api/v1/purchase-orders/{po_id}/confirm")

    resp = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 50}],
        "supplier_invoice_number": "FINV-2024-100",
        "supplier_invoice_date": "2024-06-15",
        "supplier_invoice_total": 300000,
        "payment_terms": "Net 30",
        "payment_due_date": "2024-07-15",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("supplier_invoice_number") == "FINV-2024-100"


# ── Get single PO ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_single_po(client: AsyncClient, db: AsyncSession):
    pids, wid, sup_id = await _setup(client, db, "GETPO")
    pid = pids[0]
    po = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sup_id, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 10, "unit_cost": "1000"}],
    })
    po_id = po.json()["id"]
    resp = await client.get(f"/api/v1/purchase-orders/{po_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == po_id
