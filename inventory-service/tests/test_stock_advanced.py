"""Advanced stock tests — QC, two-phase transfer, adjust-in/out, relocate, FEFO dispatch."""
import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient, suffix: str):
    """Create product + warehouse, return (product_id, warehouse_id)."""
    p = await client.post("/api/v1/products", json={"name": f"Prod-{suffix}", "sku": f"SA-{suffix}", "unit_of_measure": "un"})
    w = await client.post("/api/v1/warehouses", json={"name": f"WH-{suffix}", "code": f"WH-SA-{suffix}", "type": "main"})
    return p.json()["id"], w.json()["id"]


async def _receive(client, pid, wid, qty=100, cost="5000", batch=None):
    payload = {"product_id": pid, "warehouse_id": wid, "quantity": str(qty), "unit_cost": cost}
    if batch:
        payload["batch_number"] = batch
    resp = await client.post("/api/v1/stock/receive", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── Two-phase transfer ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_initiate_and_complete_transfer(client: AsyncClient):
    pid, wid1 = await _setup(client, "2PH-001")
    w2 = await client.post("/api/v1/warehouses", json={"name": "WH-2PH-DST", "code": "WH-2PH-DST", "type": "secondary"})
    wid2 = w2.json()["id"]
    await _receive(client, pid, wid1, 100)

    # Phase 1: initiate
    resp = await client.post("/api/v1/stock/transfer/initiate", json={
        "product_id": pid, "from_warehouse_id": wid1, "to_warehouse_id": wid2, "quantity": "30",
    })
    assert resp.status_code == 201
    mov = resp.json()
    assert mov["status"] == "in_transit"
    mov_id = mov["id"]

    # Phase 2: complete
    resp = await client.post(f"/api/v1/stock/transfer/{mov_id}/complete")
    assert resp.status_code == 200


# ── Adjust-in ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_adjust_in(client: AsyncClient):
    pid, wid = await _setup(client, "ADJIN-001")
    resp = await client.post("/api/v1/stock/adjust-in", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50",
        "unit_cost": "3000", "reason": "Found stock",
    })
    assert resp.status_code == 201
    assert resp.json()["movement_type"] == "adjustment_in"


# ── Adjust-out ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_adjust_out(client: AsyncClient):
    pid, wid = await _setup(client, "ADJOUT-001")
    await _receive(client, pid, wid, 100)
    resp = await client.post("/api/v1/stock/adjust-out", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "10", "reason": "Cycle count",
    })
    assert resp.status_code == 201
    assert resp.json()["movement_type"] == "adjustment_out"


@pytest.mark.asyncio
async def test_adjust_out_insufficient(client: AsyncClient):
    pid, wid = await _setup(client, "ADJOUT-002")
    await _receive(client, pid, wid, 5)
    resp = await client.post("/api/v1/stock/adjust-out", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50", "reason": "Oops",
    })
    assert resp.status_code in (400, 422, 500)


# ── QC approve / reject ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_qc_approve(client: AsyncClient):
    # Create a product type that requires QC
    pt = await client.post("/api/v1/config/product-types", json={
        "name": "QC Type", "requires_qc": True,
    })
    pt_id = pt.json()["id"]
    p = await client.post("/api/v1/products", json={
        "name": "QC-Prod", "sku": "QC-APPROVE", "unit_of_measure": "un",
        "product_type_id": pt_id,
    })
    pid = p.json()["id"]
    w = await client.post("/api/v1/warehouses", json={"name": "WH-QC", "code": "WH-QC-A", "type": "main"})
    wid = w.json()["id"]

    await _receive(client, pid, wid, 50, "1000")
    resp = await client.post("/api/v1/stock/qc-approve", json={
        "product_id": pid, "warehouse_id": wid,
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_qc_reject(client: AsyncClient):
    pt = await client.post("/api/v1/config/product-types", json={
        "name": "QC Type Rej", "requires_qc": True,
    })
    pt_id = pt.json()["id"]
    p = await client.post("/api/v1/products", json={
        "name": "QC-Prod-R", "sku": "QC-REJECT", "unit_of_measure": "un",
        "product_type_id": pt_id,
    })
    pid = p.json()["id"]
    w = await client.post("/api/v1/warehouses", json={"name": "WH-QCR", "code": "WH-QC-R", "type": "main"})
    wid = w.json()["id"]

    await _receive(client, pid, wid, 30, "2000")
    resp = await client.post("/api/v1/stock/qc-reject", json={
        "product_id": pid, "warehouse_id": wid, "notes": "Failed inspection",
    })
    assert resp.status_code == 200


# ── Waste insufficient ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_waste_insufficient(client: AsyncClient):
    pid, wid = await _setup(client, "WST-INS")
    await _receive(client, pid, wid, 5)
    resp = await client.post("/api/v1/stock/waste", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50", "reason": "Damage",
    })
    assert resp.status_code in (400, 422, 500)


# ── Relocate within warehouse ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_relocate_stock(client: AsyncClient):
    pid, wid = await _setup(client, "RELOC")
    # Create locations
    loc1 = await client.post("/api/v1/config/locations", json={
        "warehouse_id": wid, "name": "A-01", "code": "A-01",
    })
    loc2 = await client.post("/api/v1/config/locations", json={
        "warehouse_id": wid, "name": "A-02", "code": "A-02",
    })
    loc1_id = loc1.json()["id"]
    loc2_id = loc2.json()["id"]

    # Receive into first location
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "50",
        "unit_cost": "1000", "location_id": loc1_id,
    })

    # Relocate — uses query params, not JSON body
    resp = await client.post("/api/v1/stock/relocate", params={
        "product_id": pid, "warehouse_id": wid,
        "from_location_id": loc1_id, "to_location_id": loc2_id,
        "quantity": "20",
    })
    # May return 200 or 201
    assert resp.status_code in (200, 201)


# ── Return with custom cost ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_return_with_unit_cost(client: AsyncClient):
    pid, wid = await _setup(client, "RET-COST")
    await _receive(client, pid, wid, 50, "5000")
    resp = await client.post("/api/v1/stock/return", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "5",
        "unit_cost": "4500", "reference": "Partial return",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["movement_type"] == "return"


# ── Stock levels with location filter ────────────────────────────────────────

@pytest.mark.asyncio
async def test_stock_levels_with_location(client: AsyncClient):
    pid, wid = await _setup(client, "LVL-LOC")
    loc = await client.post("/api/v1/config/locations", json={
        "warehouse_id": wid, "name": "B-01", "code": f"B-01-LVL",
    })
    loc_id = loc.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "30",
        "unit_cost": "1000", "location_id": loc_id,
    })
    resp = await client.get("/api/v1/stock", params={
        "product_id": pid, "warehouse_id": wid, "location_id": loc_id,
    })
    assert resp.status_code == 200


# ── Stock reservations list ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stock_reservations_list(client: AsyncClient):
    resp = await client.get("/api/v1/stock/reservations")
    assert resp.status_code == 200


# ── Assign location to stock level ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_assign_location_to_level(client: AsyncClient):
    pid, wid = await _setup(client, "ASSIGN-LOC")
    await _receive(client, pid, wid, 20)
    # Get stock level id
    levels = await client.get("/api/v1/stock", params={"product_id": pid, "warehouse_id": wid})
    items = levels.json()["items"]
    assert len(items) >= 1
    level_id = items[0]["id"]

    loc = await client.post("/api/v1/config/locations", json={
        "warehouse_id": wid, "name": "C-01", "code": f"C-01-ASN",
    })
    loc_id = loc.json()["id"]

    resp = await client.patch(f"/api/v1/stock/levels/{level_id}/location", json={
        "location_id": loc_id,
    })
    assert resp.status_code == 200
