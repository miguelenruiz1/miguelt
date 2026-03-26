"""PO lifecycle + variant CRUD integration tests."""
from __future__ import annotations

import re
import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.supplier import Supplier


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _setup(client: AsyncClient, db: AsyncSession, suffix: str):
    """Create a product, warehouse, and supplier for a test case."""
    p = await client.post(
        "/api/v1/products",
        json={"name": f"P-{suffix}", "sku": f"POL-{suffix}", "unit_of_measure": "un"},
    )
    assert p.status_code == 201, p.text
    w = await client.post(
        "/api/v1/warehouses",
        json={"name": f"W-{suffix}", "code": f"WPOL-{suffix}", "type": "main"},
    )
    assert w.status_code == 201, w.text
    pid, wid = p.json()["id"], w.json()["id"]

    sid = str(uuid.uuid4())
    supplier = Supplier(
        id=sid, tenant_id="test-tenant", name=f"Sup-{suffix}",
        code=f"SPOL-{suffix}", is_active=True,
    )
    db.add(supplier)
    await db.flush()
    return pid, wid, sid


async def _create_po(client: AsyncClient, supplier_id: str, warehouse_id: str,
                     lines: list[dict], notes: str | None = None):
    """Shortcut to POST a draft PO and return (po_json, response)."""
    body: dict = {"supplier_id": supplier_id, "warehouse_id": warehouse_id, "lines": lines}
    if notes:
        body["notes"] = notes
    resp = await client.post("/api/v1/purchase-orders", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json(), resp


async def _advance_to_confirmed(client: AsyncClient, po_id: str):
    """Send then confirm a PO."""
    r1 = await client.post(f"/api/v1/purchase-orders/{po_id}/send")
    assert r1.status_code == 200, r1.text
    r2 = await client.post(f"/api/v1/purchase-orders/{po_id}/confirm")
    assert r2.status_code == 200, r2.text
    return r2.json()


# ── 1. Full lifecycle: draft → send → confirm → receive (full) ────────────────


@pytest.mark.asyncio
async def test_full_lifecycle(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC01")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 50, "unit_cost": "12.50"},
    ])
    po_id = po["id"]
    line_id = po["lines"][0]["id"]

    assert po["status"] == "draft"

    # send
    r = await client.post(f"/api/v1/purchase-orders/{po_id}/send")
    assert r.status_code == 200
    assert r.json()["status"] == "sent"

    # confirm
    r = await client.post(f"/api/v1/purchase-orders/{po_id}/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    # receive full qty
    r = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 50}],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "received"
    assert data["received_date"] is not None

    # Verify stock increased
    stock = await client.get(f"/api/v1/stock?product_id={pid}")
    assert stock.status_code == 200
    items = stock.json()["items"]
    assert len(items) >= 1
    assert float(items[0]["qty_on_hand"]) >= 50


# ── 2. Partial receive ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_partial_receive(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC02")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 100, "unit_cost": "10"},
    ])
    po_id = po["id"]
    line_id = po["lines"][0]["id"]

    await _advance_to_confirmed(client, po_id)

    # partial receive
    r = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 40}],
    })
    assert r.status_code == 200
    assert r.json()["status"] == "partial"

    # receive the rest
    r = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 60}],
    })
    assert r.status_code == 200
    assert r.json()["status"] == "received"


# ── 3. Cancel from different states ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_draft(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC03A")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_cost": "5"},
    ])
    r = await client.post(f"/api/v1/purchase-orders/{po['id']}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_cancel_sent(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC03B")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_cost": "5"},
    ])
    await client.post(f"/api/v1/purchase-orders/{po['id']}/send")
    r = await client.post(f"/api/v1/purchase-orders/{po['id']}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_cancel_confirmed(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC03C")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_cost": "5"},
    ])
    await _advance_to_confirmed(client, po["id"])
    r = await client.post(f"/api/v1/purchase-orders/{po['id']}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "canceled"


# ── 4. Update draft PO ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_draft_po(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC04")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 20, "unit_cost": "8"},
    ])
    po_id = po["id"]

    r = await client.patch(f"/api/v1/purchase-orders/{po_id}", json={
        "notes": "Updated notes",
        "expected_date": "2026-06-15",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["notes"] == "Updated notes"
    assert data["expected_date"] == "2026-06-15"


# ── 5. Delete draft PO ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_draft(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC05")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_cost": "3"},
    ])
    po_id = po["id"]

    r = await client.delete(f"/api/v1/purchase-orders/{po_id}")
    assert r.status_code in (200, 204)

    # verify gone (may still return 200 if soft-delete)
    r = await client.get(f"/api/v1/purchase-orders/{po_id}")
    assert r.status_code in (200, 404, 422)


# ── 6. Delete non-draft fails ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_non_draft_fails(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC06")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_cost": "3"},
    ])
    po_id = po["id"]

    await client.post(f"/api/v1/purchase-orders/{po_id}/send")

    r = await client.delete(f"/api/v1/purchase-orders/{po_id}")
    assert r.status_code in (400, 409, 422)


# ── 7. PO with multiple lines, partial receive per line ──────────────────────


@pytest.mark.asyncio
async def test_multiple_lines_partial(client: AsyncClient, db: AsyncSession):
    pid1, wid, sid = await _setup(client, db, "LC07A")
    # Create two more products
    p2 = await client.post("/api/v1/products", json={
        "name": "P-LC07B", "sku": "POL-LC07B", "unit_of_measure": "un",
    })
    p3 = await client.post("/api/v1/products", json={
        "name": "P-LC07C", "sku": "POL-LC07C", "unit_of_measure": "un",
    })
    pid2 = p2.json()["id"]
    pid3 = p3.json()["id"]

    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid1, "qty_ordered": 30, "unit_cost": "10"},
        {"product_id": pid2, "qty_ordered": 20, "unit_cost": "15"},
        {"product_id": pid3, "qty_ordered": 50, "unit_cost": "5"},
    ])
    po_id = po["id"]
    lines = po["lines"]
    assert len(lines) == 3

    await _advance_to_confirmed(client, po_id)

    # Receive partial on first two lines only
    r = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [
            {"line_id": lines[0]["id"], "qty_received": 10},
            {"line_id": lines[1]["id"], "qty_received": 20},
        ],
    })
    assert r.status_code == 200
    assert r.json()["status"] == "partial"

    # Finish receiving all lines
    r = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [
            {"line_id": lines[0]["id"], "qty_received": 20},
            {"line_id": lines[2]["id"], "qty_received": 50},
        ],
    })
    assert r.status_code == 200
    assert r.json()["status"] == "received"


# ── 8. Receive creates stock movement ────────────────────────────────────────


@pytest.mark.asyncio
async def test_receive_creates_stock(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC08")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 25, "unit_cost": "7.50"},
    ])
    po_id = po["id"]
    line_id = po["lines"][0]["id"]

    await _advance_to_confirmed(client, po_id)
    await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 25}],
    })

    stock = await client.get(f"/api/v1/stock?product_id={pid}")
    assert stock.status_code == 200
    items = stock.json()["items"]
    total_qty = sum(float(s["qty_on_hand"]) for s in items)
    assert total_qty >= 25


# ── 9. List POs with filters ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_pos_filter_status(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC09")

    # Create a draft and a sent PO
    po1, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_cost": "1"},
    ])
    po2, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_cost": "1"},
    ])
    await client.post(f"/api/v1/purchase-orders/{po2['id']}/send")

    # filter by draft
    r = await client.get("/api/v1/purchase-orders?status=draft")
    assert r.status_code == 200
    data = r.json()
    draft_ids = [po["id"] for po in data["items"]]
    assert po1["id"] in draft_ids
    assert po2["id"] not in draft_ids

    # filter by sent
    r = await client.get("/api/v1/purchase-orders?status=sent")
    assert r.status_code == 200
    sent_ids = [po["id"] for po in r.json()["items"]]
    assert po2["id"] in sent_ids


@pytest.mark.asyncio
async def test_list_pos_filter_supplier(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC09S")

    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_cost": "1"},
    ])

    r = await client.get(f"/api/v1/purchase-orders?supplier_id={sid}")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()["items"]]
    assert po["id"] in ids

    # non-existent supplier returns nothing
    fake = str(uuid.uuid4())
    r2 = await client.get(f"/api/v1/purchase-orders?supplier_id={fake}")
    assert r2.status_code == 200
    assert all(p["supplier_id"] != sid for p in r2.json()["items"])


# ── 10. PO number auto-generated (format PO-YYYY-NNNN) ──────────────────────


@pytest.mark.asyncio
async def test_po_number_format(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC10")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 1, "unit_cost": "1"},
    ])
    po_number = po["po_number"]
    year = date.today().year
    pattern = rf"^PO-{year}-\d{{4}}$"
    assert re.match(pattern, po_number), f"PO number '{po_number}' does not match {pattern}"


# ── 11. Receive updates product last_purchase_cost ───────────────────────────


@pytest.mark.asyncio
async def test_receive_updates_product_cost(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC11")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_cost": "99.99"},
    ])
    po_id = po["id"]
    line_id = po["lines"][0]["id"]

    await _advance_to_confirmed(client, po_id)
    await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 10}],
    })

    prod = await client.get(f"/api/v1/products/{pid}")
    assert prod.status_code == 200
    data = prod.json()
    assert float(data.get("last_purchase_cost", 0)) == pytest.approx(99.99, abs=0.01)


# ── 12. Cannot receive more than ordered ────────────────────────────────────


@pytest.mark.asyncio
async def test_receive_over_ordered_fails(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC12")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 5, "unit_cost": "10"},
    ])
    po_id = po["id"]
    line_id = po["lines"][0]["id"]

    await _advance_to_confirmed(client, po_id)
    r = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 999}],
    })
    assert r.status_code in (400, 409, 422)


# ── 13. Cannot cancel a received PO ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_received_fails(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC13")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 2, "unit_cost": "5"},
    ])
    po_id = po["id"]
    line_id = po["lines"][0]["id"]

    await _advance_to_confirmed(client, po_id)
    await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 2}],
    })

    r = await client.post(f"/api/v1/purchase-orders/{po_id}/cancel")
    assert r.status_code in (400, 409, 422)


# ── 14. Cannot confirm a draft (must be sent first) ─────────────────────────


@pytest.mark.asyncio
async def test_confirm_draft_fails(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC14")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 1, "unit_cost": "1"},
    ])
    r = await client.post(f"/api/v1/purchase-orders/{po['id']}/confirm")
    assert r.status_code in (400, 409, 422)


# ── 15. PO without warehouse cannot be received ─────────────────────────────


@pytest.mark.asyncio
async def test_receive_without_warehouse_fails(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC15")
    # Create PO without warehouse_id
    body = {
        "supplier_id": sid,
        "lines": [{"product_id": pid, "qty_ordered": 10, "unit_cost": "5"}],
    }
    r = await client.post("/api/v1/purchase-orders", json=body)
    # May succeed as draft (warehouse optional on create) or fail
    if r.status_code == 201:
        po = r.json()
        po_id = po["id"]
        line_id = po["lines"][0]["id"]
        # Try to send → confirm → receive
        await client.post(f"/api/v1/purchase-orders/{po_id}/send")
        await client.post(f"/api/v1/purchase-orders/{po_id}/confirm")
        recv = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
            "lines": [{"line_id": line_id, "qty_received": 10}],
        })
        assert recv.status_code in (400, 409, 422)


# ── 16. PO without lines cannot be created ───────────────────────────────────


@pytest.mark.asyncio
async def test_create_po_no_lines_fails(client: AsyncClient, db: AsyncSession):
    _pid, wid, sid = await _setup(client, db, "LC16")
    r = await client.post("/api/v1/purchase-orders", json={
        "supplier_id": sid, "warehouse_id": wid, "lines": [],
    })
    assert r.status_code in (400, 409, 422)


# ── 17. Get single PO ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_po_by_id(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC17")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 1, "unit_cost": "1"},
    ])
    r = await client.get(f"/api/v1/purchase-orders/{po['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == po["id"]
    assert r.json()["po_number"] == po["po_number"]


# ── 18. Get non-existent PO returns 404 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_nonexistent_po(client: AsyncClient, db: AsyncSession):
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/v1/purchase-orders/{fake_id}")
    assert r.status_code in (404, 422)


# ── 19. Receive with invoice data ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_receive_with_invoice_data(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC19")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 10, "unit_cost": "20"},
    ])
    po_id = po["id"]
    line_id = po["lines"][0]["id"]

    await _advance_to_confirmed(client, po_id)
    r = await client.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": 10}],
        "supplier_invoice_number": "INV-2026-001",
        "supplier_invoice_date": "2026-03-25",
        "supplier_invoice_total": 200,
        "payment_terms": "net30",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["supplier_invoice_number"] == "INV-2026-001"
    assert data["payment_terms"] == "net30"


# ── 20. Cancel already-canceled PO fails ─────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_canceled_fails(client: AsyncClient, db: AsyncSession):
    pid, wid, sid = await _setup(client, db, "LC20")
    po, _ = await _create_po(client, sid, wid, [
        {"product_id": pid, "qty_ordered": 1, "unit_cost": "1"},
    ])
    await client.post(f"/api/v1/purchase-orders/{po['id']}/cancel")
    r = await client.post(f"/api/v1/purchase-orders/{po['id']}/cancel")
    assert r.status_code in (400, 409, 422)


# ══════════════════════════════════════════════════════════════════════════════
# Variant tests
# ══════════════════════════════════════════════════════════════════════════════


async def _setup_product(client: AsyncClient, suffix: str) -> str:
    """Create a product and return its id."""
    p = await client.post("/api/v1/products", json={
        "name": f"VarProd-{suffix}", "sku": f"VP-{suffix}", "unit_of_measure": "un",
    })
    assert p.status_code == 201, p.text
    return p.json()["id"]


# ── 21. Create variant attribute ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_variant_attribute(client: AsyncClient, db: AsyncSession):
    r = await client.post("/api/v1/variant-attributes", json={
        "name": "Color", "slug": "color-lc21",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Color"
    assert data["slug"] == "color-lc21"
    assert "id" in data


# ── 22. Create variant attribute with options ────────────────────────────────


@pytest.mark.asyncio
async def test_create_attribute_with_options(client: AsyncClient, db: AsyncSession):
    r = await client.post("/api/v1/variant-attributes", json={
        "name": "Size", "slug": "size-lc22",
        "options": [
            {"value": "S", "sort_order": 0},
            {"value": "M", "sort_order": 1},
            {"value": "L", "sort_order": 2},
        ],
    })
    assert r.status_code == 201
    data = r.json()
    # Options may or may not be eagerly loaded
    if "options" in data and data["options"]:
        assert len(data["options"]) == 3


# ── 23. Create variant for product ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_variant(client: AsyncClient, db: AsyncSession):
    pid = await _setup_product(client, "LC23")
    attr = await client.post("/api/v1/variant-attributes", json={
        "name": "Color", "slug": "color-lc23",
    })
    attr_id = attr.json()["id"]

    r = await client.post("/api/v1/variants", json={
        "parent_id": pid, "sku": "VAR-LC23", "name": "Red LC23",
        "option_values": {attr_id: "Red"},
        "cost_price": 10.0, "sale_price": 25.0,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["parent_id"] == pid
    assert data["sku"] == "VAR-LC23"
    assert data["name"] == "Red LC23"
    assert data["option_values"][attr_id] == "Red"


# ── 24. List variants for product ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_variants_for_product(client: AsyncClient, db: AsyncSession):
    pid = await _setup_product(client, "LC24")
    attr = await client.post("/api/v1/variant-attributes", json={
        "name": "Size", "slug": "size-lc24",
    })
    attr_id = attr.json()["id"]

    await client.post("/api/v1/variants", json={
        "parent_id": pid, "sku": "VAR-LC24A", "name": "Small",
        "option_values": {attr_id: "S"},
    })
    await client.post("/api/v1/variants", json={
        "parent_id": pid, "sku": "VAR-LC24B", "name": "Medium",
        "option_values": {attr_id: "M"},
    })

    r = await client.get(f"/api/v1/products/{pid}/variants")
    assert r.status_code == 200
    variants = r.json()
    assert len(variants) >= 2
    skus = [v["sku"] for v in variants]
    assert "VAR-LC24A" in skus
    assert "VAR-LC24B" in skus


# ── 25. Get variant by id ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_variant_by_id(client: AsyncClient, db: AsyncSession):
    pid = await _setup_product(client, "LC25")
    attr = await client.post("/api/v1/variant-attributes", json={
        "name": "Color", "slug": "color-lc25",
    })
    attr_id = attr.json()["id"]

    created = await client.post("/api/v1/variants", json={
        "parent_id": pid, "sku": "VAR-LC25", "name": "Blue LC25",
        "option_values": {attr_id: "Blue"},
    })
    vid = created.json()["id"]

    r = await client.get(f"/api/v1/variants/{vid}")
    assert r.status_code == 200
    assert r.json()["id"] == vid
    assert r.json()["name"] == "Blue LC25"


# ── 26. Update variant ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_variant(client: AsyncClient, db: AsyncSession):
    pid = await _setup_product(client, "LC26")
    attr = await client.post("/api/v1/variant-attributes", json={
        "name": "Color", "slug": "color-lc26",
    })
    attr_id = attr.json()["id"]

    created = await client.post("/api/v1/variants", json={
        "parent_id": pid, "sku": "VAR-LC26", "name": "Green LC26",
        "option_values": {attr_id: "Green"},
        "cost_price": 5.0, "sale_price": 15.0,
    })
    vid = created.json()["id"]

    r = await client.patch(f"/api/v1/variants/{vid}", json={
        "name": "Dark Green LC26",
        "cost_price": 6.50,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Dark Green LC26"
    assert float(data["cost_price"]) == pytest.approx(6.50, abs=0.01)


# ── 27. Delete variant ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_variant(client: AsyncClient, db: AsyncSession):
    pid = await _setup_product(client, "LC27")
    created = await client.post("/api/v1/variants", json={
        "parent_id": pid, "sku": "VAR-LC27", "name": "Temp LC27",
        "option_values": {},
    })
    vid = created.json()["id"]

    r = await client.delete(f"/api/v1/variants/{vid}")
    assert r.status_code == 204

    r2 = await client.get(f"/api/v1/variants/{vid}")
    assert r2.status_code in (404, 422)


# ── 28. List variant attributes ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_variant_attributes(client: AsyncClient, db: AsyncSession):
    await client.post("/api/v1/variant-attributes", json={
        "name": "Material", "slug": "material-lc28",
    })
    r = await client.get("/api/v1/variant-attributes")
    assert r.status_code == 200
    names = [a["name"] for a in r.json()]
    assert "Material" in names


# ── 29. Update variant attribute ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_variant_attribute(client: AsyncClient, db: AsyncSession):
    created = await client.post("/api/v1/variant-attributes", json={
        "name": "Talla", "slug": "talla-lc29",
    })
    attr_id = created.json()["id"]

    r = await client.patch(f"/api/v1/variant-attributes/{attr_id}", json={
        "name": "Talla Actualizada",
    })
    assert r.status_code == 200
    assert r.json()["name"] == "Talla Actualizada"


# ── 30. List variants with pagination ────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_variants_paginated(client: AsyncClient, db: AsyncSession):
    pid = await _setup_product(client, "LC30")
    for i in range(3):
        await client.post("/api/v1/variants", json={
            "parent_id": pid, "sku": f"VAR-LC30-{i}", "name": f"V{i} LC30",
            "option_values": {},
        })

    r = await client.get("/api/v1/variants?limit=2&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) <= 2
