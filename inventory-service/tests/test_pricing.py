"""Tests for pricing engine — margins, suggested prices, cost methods, validation."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Supplier


async def _setup_product_with_cost(client: AsyncClient, db: AsyncSession, suffix: str):
    """Create product, warehouse, supplier, receive stock (sets last_purchase_cost)."""
    import uuid
    p = await client.post("/api/v1/products", json={
        "name": f"Prod-{suffix}", "sku": f"PRC-{suffix}", "unit_of_measure": "un",
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{suffix}", "code": f"WH-PRC-{suffix}", "type": "main",
    })
    pid, wid = p.json()["id"], w.json()["id"]

    # Create supplier in DB
    sup_id = str(uuid.uuid4())
    supplier = Supplier(
        id=sup_id, tenant_id="test-tenant", name=f"Sup-{suffix}",
        code=f"SPRC-{suffix}", is_active=True,
    )
    db.add(supplier)
    await db.flush()

    # Create PO and receive (sets last_purchase_cost)
    po = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sup_id, "warehouse_id": wid,
        "lines": [{"product_id": pid, "qty_ordered": 100, "unit_cost": "5000"}],
    })
    po_data = po.json()
    po_id = po_data["id"]
    line_id = po_data["lines"][0]["id"]

    await client.post(f"/api/v1/purchase-orders/{po_id}/send")
    await client.post(f"/api/v1/purchase-orders/{po_id}/confirm")
    await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 100}],
    })

    return pid, wid, sup_id


# ── Product pricing view ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_product_pricing(client: AsyncClient, db: AsyncSession):
    pid, _, _ = await _setup_product_with_cost(client, db, "VIEW")
    resp = await client.get(f"/api/v1/products/{pid}/pricing")
    assert resp.status_code == 200
    data = resp.json()
    assert "last_purchase_cost" in data


# ── Update product margins ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_product_margins(client: AsyncClient, db: AsyncSession):
    pid, _, _ = await _setup_product_with_cost(client, db, "MARGIN")
    resp = await client.patch(f"/api/v1/products/{pid}/margins", json={
        "margin_target": 30, "margin_minimum": 15,
    })
    assert resp.status_code == 200


# ── Cost history ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_product_cost_history(client: AsyncClient, db: AsyncSession):
    pid, _, _ = await _setup_product_with_cost(client, db, "COSTHIST")
    resp = await client.get(f"/api/v1/products/{pid}/cost-history")
    assert resp.status_code == 200
    data = resp.json()
    items = data.get("items", data) if isinstance(data, dict) else data
    assert len(items) >= 1


# ── Multiple PO receives build cost history ──────────────────────────────────

@pytest.mark.asyncio
async def test_multiple_purchases_cost_history(client: AsyncClient, db: AsyncSession):
    import uuid as _uuid
    p = await client.post("/api/v1/products", json={
        "name": "MultiCost", "sku": "PRC-MULTI", "unit_of_measure": "un",
    })
    w = await client.post("/api/v1/warehouses", json={
        "name": "WH-MULTI", "code": "WH-PRC-MULTI", "type": "main",
    })
    pid, wid = p.json()["id"], w.json()["id"]

    sup_id = str(_uuid.uuid4())
    supplier = Supplier(id=sup_id, tenant_id="test-tenant", name="Sup-Multi", code="SPRC-MULTI", is_active=True)
    db.add(supplier)
    await db.flush()

    for cost in ["3000", "4000", "5000"]:
        po = await client.post("/api/v1/purchase-orders", json={
            "supplier_id": sup_id, "warehouse_id": wid,
            "lines": [{"product_id": pid, "qty_ordered": 50, "unit_cost": cost}],
        })
        po_data = po.json()
        await client.post(f"/api/v1/purchase-orders/{po_data['id']}/send")
        await client.post(f"/api/v1/purchase-orders/{po_data['id']}/confirm")
        await client.post(f"/api/v1/purchase-orders/{po_data['id']}/receive", json={
            "lines": [{"line_id": po_data['lines'][0]['id'], "qty_received": 50}],
        })

    resp = await client.get(f"/api/v1/products/{pid}/cost-history")
    assert resp.status_code == 200
    data = resp.json()
    items = data.get("items", data) if isinstance(data, dict) else data
    assert len(items) >= 3
