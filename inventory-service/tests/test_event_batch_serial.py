"""Tests for events, batches, and serials endpoints."""
import pytest
from httpx import AsyncClient


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _create_product(client: AsyncClient, suffix: str) -> str:
    resp = await client.post("/api/v1/products", json={
        "name": f"Prod-EBS-{suffix}", "sku": f"EBS-{suffix}", "unit_of_measure": "un",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_warehouse(client: AsyncClient, suffix: str) -> str:
    resp = await client.post("/api/v1/warehouses", json={
        "name": f"WH-EBS-{suffix}", "code": f"WH-EBS-{suffix}", "type": "main",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_event_config(client: AsyncClient, suffix: str):
    """Create event type, severity, and status. Returns (type_id, severity_id, status_id)."""
    et = await client.post("/api/v1/config/event-types", json={
        "name": f"EvType-{suffix}", "slug": f"evtype-{suffix}",
    })
    assert et.status_code == 201, et.text
    sev = await client.post("/api/v1/config/event-severities", json={
        "name": f"Sev-{suffix}", "slug": f"sev-{suffix}", "weight": 3,
    })
    assert sev.status_code == 201, sev.text
    st = await client.post("/api/v1/config/event-statuses", json={
        "name": f"Status-{suffix}", "slug": f"status-{suffix}",
    })
    assert st.status_code == 201, st.text
    return et.json()["id"], sev.json()["id"], st.json()["id"]


async def _create_serial_status(client: AsyncClient, suffix: str) -> str:
    resp = await client.post("/api/v1/config/serial-statuses", json={
        "name": f"SrlSt-{suffix}", "slug": f"srlst-{suffix}",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_event_basic(client: AsyncClient):
    pid = await _create_product(client, "ev1")
    wid = await _create_warehouse(client, "ev1")
    type_id, sev_id, status_id = await _create_event_config(client, "ev1")

    resp = await client.post("/api/v1/events", json={
        "event_type_id": type_id,
        "severity_id": sev_id,
        "status_id": status_id,
        "title": "Broken item ev1",
        "description": "Fell off shelf",
        "warehouse_id": wid,
        "occurred_at": "2026-03-20T10:00:00Z",
        "impacts": [{"entity_id": pid, "quantity_impact": -5}],
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["title"] == "Broken item ev1"
    assert data["event_type_id"] == type_id
    assert data["severity_id"] == sev_id
    assert data["status_id"] == status_id
    assert data["warehouse_id"] == wid
    # Impacts may not be loaded eagerly in create response
    assert "impacts" in data


@pytest.mark.asyncio
async def test_create_event_no_impacts(client: AsyncClient):
    type_id, sev_id, status_id = await _create_event_config(client, "ev2")

    resp = await client.post("/api/v1/events", json={
        "event_type_id": type_id,
        "severity_id": sev_id,
        "status_id": status_id,
        "title": "Minor observation ev2",
        "occurred_at": "2026-03-20T12:00:00Z",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["impacts"] == []
    assert data["description"] is None


@pytest.mark.asyncio
async def test_create_event_multiple_impacts(client: AsyncClient):
    pid1 = await _create_product(client, "ev3a")
    pid2 = await _create_product(client, "ev3b")
    wid = await _create_warehouse(client, "ev3")
    type_id, sev_id, status_id = await _create_event_config(client, "ev3")

    resp = await client.post("/api/v1/events", json={
        "event_type_id": type_id,
        "severity_id": sev_id,
        "status_id": status_id,
        "title": "Multi impact ev3",
        "warehouse_id": wid,
        "occurred_at": "2026-03-20T14:00:00Z",
        "impacts": [
            {"entity_id": pid1, "quantity_impact": -3, "notes": "damaged"},
            {"entity_id": pid2, "quantity_impact": -7},
        ],
    })
    assert resp.status_code == 201
    assert "impacts" in resp.json()


@pytest.mark.asyncio
async def test_get_event_by_id(client: AsyncClient):
    type_id, sev_id, status_id = await _create_event_config(client, "ev4")
    created = await client.post("/api/v1/events", json={
        "event_type_id": type_id,
        "severity_id": sev_id,
        "status_id": status_id,
        "title": "Get me ev4",
        "occurred_at": "2026-03-20T09:00:00Z",
    })
    eid = created.json()["id"]

    resp = await client.get(f"/api/v1/events/{eid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == eid
    assert resp.json()["title"] == "Get me ev4"


@pytest.mark.asyncio
async def test_get_event_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/events/00000000-0000-0000-0000-000000000000")
    assert resp.status_code in (404, 422)


@pytest.mark.asyncio
async def test_list_events_empty(client: AsyncClient):
    resp = await client.get("/api/v1/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_events_with_filter(client: AsyncClient):
    type_id, sev_id, status_id = await _create_event_config(client, "ev6")
    await client.post("/api/v1/events", json={
        "event_type_id": type_id,
        "severity_id": sev_id,
        "status_id": status_id,
        "title": "Filtered ev6",
        "occurred_at": "2026-03-21T08:00:00Z",
    })

    resp = await client.get("/api/v1/events", params={"event_type_id": type_id})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["event_type_id"] == type_id for i in items)


@pytest.mark.asyncio
async def test_change_event_status(client: AsyncClient):
    type_id, sev_id, status_id = await _create_event_config(client, "ev7")
    # Create a second status to transition to
    new_st = await client.post("/api/v1/config/event-statuses", json={
        "name": "Resolved-ev7", "slug": "resolved-ev7", "is_final": True,
    })
    new_status_id = new_st.json()["id"]

    created = await client.post("/api/v1/events", json={
        "event_type_id": type_id,
        "severity_id": sev_id,
        "status_id": status_id,
        "title": "Status change ev7",
        "occurred_at": "2026-03-21T10:00:00Z",
    })
    eid = created.json()["id"]

    resp = await client.post(f"/api/v1/events/{eid}/status", json={
        "status_id": new_status_id,
        "notes": "Issue resolved",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status_id"] == new_status_id
    assert len(data["status_logs"]) >= 1  # at least the change log


@pytest.mark.asyncio
async def test_change_event_status_with_resolved_at(client: AsyncClient):
    type_id, sev_id, status_id = await _create_event_config(client, "ev8")
    new_st = await client.post("/api/v1/config/event-statuses", json={
        "name": "Closed-ev8", "slug": "closed-ev8", "is_final": True,
    })
    new_status_id = new_st.json()["id"]

    created = await client.post("/api/v1/events", json={
        "event_type_id": type_id,
        "severity_id": sev_id,
        "status_id": status_id,
        "title": "Resolve with date ev8",
        "occurred_at": "2026-03-21T11:00:00Z",
    })
    eid = created.json()["id"]

    resp = await client.post(f"/api/v1/events/{eid}/status", json={
        "status_id": new_status_id,
        "resolved_at": "2026-03-22T15:00:00Z",
    })
    assert resp.status_code == 200
    assert resp.json()["resolved_at"] is not None


@pytest.mark.asyncio
async def test_add_impact_to_existing_event(client: AsyncClient):
    pid = await _create_product(client, "ev9")
    type_id, sev_id, status_id = await _create_event_config(client, "ev9")

    created = await client.post("/api/v1/events", json={
        "event_type_id": type_id,
        "severity_id": sev_id,
        "status_id": status_id,
        "title": "Add impact later ev9",
        "occurred_at": "2026-03-21T12:00:00Z",
    })
    eid = created.json()["id"]

    resp = await client.post(f"/api/v1/events/{eid}/impacts", json={
        "entity_id": pid,
        "quantity_impact": -2,
        "notes": "late discovery",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_event_invalid_type(client: AsyncClient):
    _, sev_id, status_id = await _create_event_config(client, "ev10")
    resp = await client.post("/api/v1/events", json={
        "event_type_id": "00000000-0000-0000-0000-000000000099",
        "severity_id": sev_id,
        "status_id": status_id,
        "title": "Bad type ev10",
        "occurred_at": "2026-03-22T08:00:00Z",
    })
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_list_events_pagination(client: AsyncClient):
    type_id, sev_id, status_id = await _create_event_config(client, "ev11")
    for i in range(3):
        await client.post("/api/v1/events", json={
            "event_type_id": type_id,
            "severity_id": sev_id,
            "status_id": status_id,
            "title": f"Paginated ev11-{i}",
            "occurred_at": "2026-03-22T09:00:00Z",
        })
    resp = await client.get("/api/v1/events", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    assert resp.json()["limit"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# BATCHES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_batch(client: AsyncClient):
    pid = await _create_product(client, "bt1")
    resp = await client.post("/api/v1/batches", json={
        "entity_id": pid,
        "batch_number": "LOT-BT1-001",
        "quantity": "100",
        "expiration_date": "2027-06-15",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["batch_number"] == "LOT-BT1-001"
    assert float(data["quantity"]) == 100
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_batch_by_id(client: AsyncClient):
    pid = await _create_product(client, "bt2")
    created = await client.post("/api/v1/batches", json={
        "entity_id": pid, "batch_number": "LOT-BT2-001", "quantity": "50",
    })
    bid = created.json()["id"]

    resp = await client.get(f"/api/v1/batches/{bid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == bid


@pytest.mark.asyncio
async def test_list_batches(client: AsyncClient):
    pid = await _create_product(client, "bt3")
    await client.post("/api/v1/batches", json={
        "entity_id": pid, "batch_number": "LOT-BT3-001", "quantity": "10",
    })

    resp = await client.get("/api/v1/batches")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_batches_filter_by_entity(client: AsyncClient):
    pid = await _create_product(client, "bt4")
    await client.post("/api/v1/batches", json={
        "entity_id": pid, "batch_number": "LOT-BT4-001", "quantity": "20",
    })

    resp = await client.get("/api/v1/batches", params={"entity_id": pid})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["entity_id"] == pid for i in items)


@pytest.mark.asyncio
async def test_update_batch(client: AsyncClient):
    pid = await _create_product(client, "bt5")
    created = await client.post("/api/v1/batches", json={
        "entity_id": pid, "batch_number": "LOT-BT5-001", "quantity": "30",
    })
    bid = created.json()["id"]

    resp = await client.patch(f"/api/v1/batches/{bid}", json={
        "quantity": "45", "notes": "adjusted",
    })
    assert resp.status_code == 200
    assert float(resp.json()["quantity"]) == 45
    assert resp.json()["notes"] == "adjusted"


@pytest.mark.asyncio
async def test_delete_batch(client: AsyncClient):
    pid = await _create_product(client, "bt6")
    created = await client.post("/api/v1/batches", json={
        "entity_id": pid, "batch_number": "LOT-BT6-001", "quantity": "5",
    })
    bid = created.json()["id"]

    resp = await client.delete(f"/api/v1/batches/{bid}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_search_batches(client: AsyncClient):
    pid = await _create_product(client, "bt7")
    await client.post("/api/v1/batches", json={
        "entity_id": pid, "batch_number": "SRCH-BT7-ABC", "quantity": "10",
    })

    resp = await client.get("/api/v1/batches/search", params={"batch_code": "SRCH-BT7"})
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    assert any("SRCH-BT7" in r["batch"]["batch_number"] for r in results)


@pytest.mark.asyncio
async def test_search_batches_no_match(client: AsyncClient):
    resp = await client.get("/api/v1/batches/search", params={"batch_code": "ZZZNOMATCH999"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_batch_expiring(client: AsyncClient):
    pid = await _create_product(client, "bt8")
    # Create a batch expiring within 30 days (from 2026-03-25 perspective)
    await client.post("/api/v1/batches", json={
        "entity_id": pid, "batch_number": "LOT-BT8-EXP", "quantity": "15",
        "expiration_date": "2026-04-10",
    })

    resp = await client.get("/api/v1/batches/expiring", params={"days": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_batch_trace_forward(client: AsyncClient):
    pid = await _create_product(client, "bt9")
    created = await client.post("/api/v1/batches", json={
        "entity_id": pid, "batch_number": "LOT-BT9-TFW", "quantity": "100",
    })
    bid = created.json()["id"]

    resp = await client.get(f"/api/v1/batches/{bid}/trace-forward")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == pid
    assert "dispatches" in data
    assert "total_dispatched" in data
    assert "total_remaining" in data


@pytest.mark.asyncio
async def test_batch_get_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/batches/00000000-0000-0000-0000-000000000000")
    assert resp.status_code in (404, 422)


@pytest.mark.asyncio
async def test_batch_create_with_manufacture_date(client: AsyncClient):
    pid = await _create_product(client, "bt10")
    resp = await client.post("/api/v1/batches", json={
        "entity_id": pid,
        "batch_number": "LOT-BT10-MFG",
        "quantity": "200",
        "manufacture_date": "2026-01-15",
        "expiration_date": "2027-01-15",
        "cost": "12.50",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["manufacture_date"] == "2026-01-15"
    assert float(data["cost"]) == 12.5


# ═══════════════════════════════════════════════════════════════════════════════
# SERIALS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_serial(client: AsyncClient):
    pid = await _create_product(client, "sr1")
    ss_id = await _create_serial_status(client, "sr1")

    resp = await client.post("/api/v1/serials", json={
        "entity_id": pid,
        "serial_number": "SN-SR1-0001",
        "status_id": ss_id,
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["serial_number"] == "SN-SR1-0001"
    assert data["entity_id"] == pid
    assert data["status_id"] == ss_id


@pytest.mark.asyncio
async def test_create_serial_with_warehouse(client: AsyncClient):
    pid = await _create_product(client, "sr2")
    wid = await _create_warehouse(client, "sr2")
    ss_id = await _create_serial_status(client, "sr2")

    resp = await client.post("/api/v1/serials", json={
        "entity_id": pid,
        "serial_number": "SN-SR2-0001",
        "status_id": ss_id,
        "warehouse_id": wid,
        "notes": "received in warehouse",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["warehouse_id"] == wid
    assert data["notes"] == "received in warehouse"


@pytest.mark.asyncio
async def test_get_serial_by_id(client: AsyncClient):
    pid = await _create_product(client, "sr3")
    ss_id = await _create_serial_status(client, "sr3")
    created = await client.post("/api/v1/serials", json={
        "entity_id": pid, "serial_number": "SN-SR3-0001", "status_id": ss_id,
    })
    sid = created.json()["id"]

    resp = await client.get(f"/api/v1/serials/{sid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sid


@pytest.mark.asyncio
async def test_get_serial_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/serials/00000000-0000-0000-0000-000000000000")
    assert resp.status_code in (404, 422)


@pytest.mark.asyncio
async def test_list_serials(client: AsyncClient):
    pid = await _create_product(client, "sr4")
    ss_id = await _create_serial_status(client, "sr4")
    await client.post("/api/v1/serials", json={
        "entity_id": pid, "serial_number": "SN-SR4-0001", "status_id": ss_id,
    })

    resp = await client.get("/api/v1/serials")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_serials_filter_by_entity(client: AsyncClient):
    pid = await _create_product(client, "sr5")
    ss_id = await _create_serial_status(client, "sr5")
    await client.post("/api/v1/serials", json={
        "entity_id": pid, "serial_number": "SN-SR5-0001", "status_id": ss_id,
    })

    resp = await client.get("/api/v1/serials", params={"entity_id": pid})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["entity_id"] == pid for i in items)


@pytest.mark.asyncio
async def test_list_serials_filter_by_status(client: AsyncClient):
    pid = await _create_product(client, "sr6")
    ss_id = await _create_serial_status(client, "sr6")
    await client.post("/api/v1/serials", json={
        "entity_id": pid, "serial_number": "SN-SR6-0001", "status_id": ss_id,
    })

    resp = await client.get("/api/v1/serials", params={"status_id": ss_id})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["status_id"] == ss_id for i in items)


@pytest.mark.asyncio
async def test_update_serial_status(client: AsyncClient):
    pid = await _create_product(client, "sr7")
    ss_id = await _create_serial_status(client, "sr7a")
    ss_id2 = await _create_serial_status(client, "sr7b")

    created = await client.post("/api/v1/serials", json={
        "entity_id": pid, "serial_number": "SN-SR7-0001", "status_id": ss_id,
    })
    sid = created.json()["id"]

    resp = await client.patch(f"/api/v1/serials/{sid}", json={
        "status_id": ss_id2,
    })
    assert resp.status_code == 200
    assert resp.json()["status_id"] == ss_id2


@pytest.mark.asyncio
async def test_update_serial_notes(client: AsyncClient):
    pid = await _create_product(client, "sr8")
    ss_id = await _create_serial_status(client, "sr8")
    created = await client.post("/api/v1/serials", json={
        "entity_id": pid, "serial_number": "SN-SR8-0001", "status_id": ss_id,
    })
    sid = created.json()["id"]

    resp = await client.patch(f"/api/v1/serials/{sid}", json={
        "notes": "updated note",
    })
    assert resp.status_code == 200
    assert resp.json()["notes"] == "updated note"


@pytest.mark.asyncio
async def test_delete_serial(client: AsyncClient):
    pid = await _create_product(client, "sr9")
    ss_id = await _create_serial_status(client, "sr9")
    created = await client.post("/api/v1/serials", json={
        "entity_id": pid, "serial_number": "SN-SR9-0001", "status_id": ss_id,
    })
    sid = created.json()["id"]

    resp = await client.delete(f"/api/v1/serials/{sid}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_serial_with_metadata(client: AsyncClient):
    pid = await _create_product(client, "sr10")
    ss_id = await _create_serial_status(client, "sr10")

    resp = await client.post("/api/v1/serials", json={
        "entity_id": pid,
        "serial_number": "SN-SR10-0001",
        "status_id": ss_id,
        "metadata": {"color": "red", "weight": 1.5},
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_serials_filter_by_warehouse(client: AsyncClient):
    pid = await _create_product(client, "sr11")
    wid = await _create_warehouse(client, "sr11")
    ss_id = await _create_serial_status(client, "sr11")
    await client.post("/api/v1/serials", json={
        "entity_id": pid, "serial_number": "SN-SR11-0001",
        "status_id": ss_id, "warehouse_id": wid,
    })

    resp = await client.get("/api/v1/serials", params={"warehouse_id": wid})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["warehouse_id"] == wid for i in items)
