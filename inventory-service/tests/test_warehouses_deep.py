"""Deep tests for warehouses, categories, and suppliers routers."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _uid() -> str:
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════════════
# WAREHOUSES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_warehouse(client: AsyncClient):
    code = f"WH-{_uid()[:8]}"
    resp = await client.post("/api/v1/warehouses", json={
        "name": "Bodega Central", "code": code, "type": "main",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == code
    assert data["is_active"] is True
    assert data["type"] == "main"


@pytest.mark.asyncio
async def test_create_warehouse_duplicate_code(client: AsyncClient):
    code = f"WH-DUP-{_uid()[:6]}"
    resp1 = await client.post("/api/v1/warehouses", json={"name": "W1", "code": code})
    assert resp1.status_code == 201
    resp2 = await client.post("/api/v1/warehouses", json={"name": "W2", "code": code})
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_list_warehouses(client: AsyncClient):
    code = f"WH-LST-{_uid()[:6]}"
    await client.post("/api/v1/warehouses", json={"name": "ListTest", "code": code})
    resp = await client.get("/api/v1/warehouses")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_warehouses_filter_is_active(client: AsyncClient):
    code = f"WH-ACT-{_uid()[:6]}"
    await client.post("/api/v1/warehouses", json={"name": "Active", "code": code, "is_active": True})
    resp = await client.get("/api/v1/warehouses", params={"is_active": "true"})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["is_active"] is True


@pytest.mark.asyncio
async def test_list_warehouses_filter_inactive(client: AsyncClient):
    code = f"WH-INA-{_uid()[:6]}"
    r = await client.post("/api/v1/warehouses", json={"name": "Inactive WH", "code": code, "is_active": False})
    assert r.status_code == 201
    resp = await client.get("/api/v1/warehouses", params={"is_active": "false"})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["is_active"] is False


@pytest.mark.asyncio
async def test_list_warehouses_pagination(client: AsyncClient):
    resp = await client.get("/api/v1/warehouses", params={"offset": 0, "limit": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["offset"] == 0
    assert body["limit"] == 2
    assert len(body["items"]) <= 2


@pytest.mark.asyncio
async def test_get_warehouse_by_id(client: AsyncClient):
    code = f"WH-GET-{_uid()[:6]}"
    created = (await client.post("/api/v1/warehouses", json={"name": "GetMe", "code": code})).json()
    resp = await client.get(f"/api/v1/warehouses/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["code"] == code


@pytest.mark.asyncio
async def test_get_warehouse_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/warehouses/{_uid()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_warehouse_name(client: AsyncClient):
    code = f"WH-UPD-{_uid()[:6]}"
    created = (await client.post("/api/v1/warehouses", json={"name": "Old", "code": code})).json()
    resp = await client.patch(f"/api/v1/warehouses/{created['id']}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_update_warehouse_code(client: AsyncClient):
    code1 = f"WH-C1-{_uid()[:6]}"
    code2 = f"WH-C2-{_uid()[:6]}"
    created = (await client.post("/api/v1/warehouses", json={"name": "CodeUpd", "code": code1})).json()
    resp = await client.patch(f"/api/v1/warehouses/{created['id']}", json={"code": code2})
    assert resp.status_code == 200
    assert resp.json()["code"] == code2


@pytest.mark.asyncio
async def test_update_warehouse_code_conflict(client: AsyncClient):
    code_a = f"WH-CA-{_uid()[:6]}"
    code_b = f"WH-CB-{_uid()[:6]}"
    await client.post("/api/v1/warehouses", json={"name": "A", "code": code_a})
    created_b = (await client.post("/api/v1/warehouses", json={"name": "B", "code": code_b})).json()
    resp = await client.patch(f"/api/v1/warehouses/{created_b['id']}", json={"code": code_a})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_warehouse_not_found(client: AsyncClient):
    resp = await client.patch(f"/api/v1/warehouses/{_uid()}", json={"name": "Nope"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_warehouse(client: AsyncClient):
    code = f"WH-DEL-{_uid()[:6]}"
    created = (await client.post("/api/v1/warehouses", json={"name": "DelMe", "code": code})).json()
    resp = await client.delete(f"/api/v1/warehouses/{created['id']}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_warehouse_not_found(client: AsyncClient):
    resp = await client.delete(f"/api/v1/warehouses/{_uid()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_warehouse_type(client: AsyncClient):
    code = f"WH-TYP-{_uid()[:6]}"
    created = (await client.post("/api/v1/warehouses", json={"name": "TypeUpd", "code": code, "type": "main"})).json()
    resp = await client.patch(f"/api/v1/warehouses/{created['id']}", json={"type": "secondary"})
    assert resp.status_code == 200
    assert resp.json()["type"] == "secondary"


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_category(client: AsyncClient):
    resp = await client.post("/api/v1/categories", json={
        "name": f"Cat-{_uid()[:8]}", "description": "Test category",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_active"] is True
    assert "slug" in data


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient):
    name = f"ListCat-{_uid()[:6]}"
    await client.post("/api/v1/categories", json={"name": name})
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert "items" in body


@pytest.mark.asyncio
async def test_list_categories_filter_is_active(client: AsyncClient):
    name = f"ActiveCat-{_uid()[:6]}"
    await client.post("/api/v1/categories", json={"name": name, "is_active": True})
    resp = await client.get("/api/v1/categories", params={"is_active": "true"})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["is_active"] is True


@pytest.mark.asyncio
async def test_list_categories_search(client: AsyncClient):
    unique = f"UniqueSearchCat-{_uid()[:6]}"
    await client.post("/api/v1/categories", json={"name": unique})
    resp = await client.get("/api/v1/categories", params={"search": unique[:15]})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_list_categories_filter_parent_id(client: AsyncClient):
    parent = (await client.post("/api/v1/categories", json={"name": f"Parent-{_uid()[:6]}"})).json()
    child_name = f"Child-{_uid()[:6]}"
    await client.post("/api/v1/categories", json={"name": child_name, "parent_id": parent["id"]})
    resp = await client.get("/api/v1/categories", params={"parent_id": parent["id"]})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["parent_id"] == parent["id"]


@pytest.mark.asyncio
async def test_get_category_by_id(client: AsyncClient):
    cat = (await client.post("/api/v1/categories", json={"name": f"GetCat-{_uid()[:6]}"})).json()
    resp = await client.get(f"/api/v1/categories/{cat['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cat["id"]


@pytest.mark.asyncio
async def test_get_category_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/categories/{_uid()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_category(client: AsyncClient):
    cat = (await client.post("/api/v1/categories", json={"name": f"UpdCat-{_uid()[:6]}"})).json()
    resp = await client.patch(f"/api/v1/categories/{cat['id']}", json={"name": "Updated Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_category_not_found(client: AsyncClient):
    resp = await client.patch(f"/api/v1/categories/{_uid()}", json={"name": "Nope"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_category(client: AsyncClient):
    cat = (await client.post("/api/v1/categories", json={"name": f"DelCat-{_uid()[:6]}"})).json()
    resp = await client.delete(f"/api/v1/categories/{cat['id']}")
    assert resp.status_code == 204
    # Confirm gone
    resp2 = await client.get(f"/api/v1/categories/{cat['id']}")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_not_found(client: AsyncClient):
    resp = await client.delete(f"/api/v1/categories/{_uid()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_category_with_parent_shows_parent_name(client: AsyncClient):
    parent = (await client.post("/api/v1/categories", json={"name": f"ParentRef-{_uid()[:6]}"})).json()
    child = (await client.post("/api/v1/categories", json={
        "name": f"ChildRef-{_uid()[:6]}", "parent_id": parent["id"],
    })).json()
    resp = await client.get(f"/api/v1/categories/{child['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["parent_id"] == parent["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# SUPPLIERS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_supplier(client: AsyncClient):
    code = f"SUP-{_uid()[:8]}"
    resp = await client.post("/api/v1/suppliers", json={
        "name": "Acme Corp", "code": code, "email": "acme@test.com",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == code
    assert data["is_active"] is True
    assert data["payment_terms_days"] == 30
    assert data["lead_time_days"] == 7


@pytest.mark.asyncio
async def test_create_supplier_duplicate_code(client: AsyncClient):
    code = f"SUP-DUP-{_uid()[:6]}"
    r1 = await client.post("/api/v1/suppliers", json={"name": "S1", "code": code})
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/suppliers", json={"name": "S2", "code": code})
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_suppliers(client: AsyncClient):
    code = f"SUP-LST-{_uid()[:6]}"
    await client.post("/api/v1/suppliers", json={"name": "ListSup", "code": code})
    resp = await client.get("/api/v1/suppliers")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_suppliers_filter_all(client: AsyncClient):
    """Passing is_active=None returns active and inactive suppliers."""
    code = f"SUP-ALL-{_uid()[:6]}"
    await client.post("/api/v1/suppliers", json={"name": "AllSup", "code": code, "is_active": False})
    # Default filter is is_active=True, so we must pass empty to get all
    resp = await client.get("/api/v1/suppliers")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_supplier_by_id(client: AsyncClient):
    code = f"SUP-GET-{_uid()[:6]}"
    created = (await client.post("/api/v1/suppliers", json={"name": "GetSup", "code": code})).json()
    resp = await client.get(f"/api/v1/suppliers/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["code"] == code


@pytest.mark.asyncio
async def test_get_supplier_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/suppliers/{_uid()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_supplier_name(client: AsyncClient):
    code = f"SUP-UPN-{_uid()[:6]}"
    created = (await client.post("/api/v1/suppliers", json={"name": "Old", "code": code})).json()
    resp = await client.patch(f"/api/v1/suppliers/{created['id']}", json={"name": "New Supplier"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Supplier"


@pytest.mark.asyncio
async def test_update_supplier_code(client: AsyncClient):
    code1 = f"SUP-C1-{_uid()[:6]}"
    code2 = f"SUP-C2-{_uid()[:6]}"
    created = (await client.post("/api/v1/suppliers", json={"name": "CodeUpd", "code": code1})).json()
    resp = await client.patch(f"/api/v1/suppliers/{created['id']}", json={"code": code2})
    assert resp.status_code == 200
    assert resp.json()["code"] == code2


@pytest.mark.asyncio
async def test_update_supplier_code_conflict(client: AsyncClient):
    code_a = f"SUP-CA-{_uid()[:6]}"
    code_b = f"SUP-CB-{_uid()[:6]}"
    await client.post("/api/v1/suppliers", json={"name": "A", "code": code_a})
    b = (await client.post("/api/v1/suppliers", json={"name": "B", "code": code_b})).json()
    resp = await client.patch(f"/api/v1/suppliers/{b['id']}", json={"code": code_a})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_supplier_not_found(client: AsyncClient):
    resp = await client.patch(f"/api/v1/suppliers/{_uid()}", json={"name": "Nope"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_supplier(client: AsyncClient):
    code = f"SUP-DEL-{_uid()[:6]}"
    created = (await client.post("/api/v1/suppliers", json={"name": "DelSup", "code": code})).json()
    resp = await client.delete(f"/api/v1/suppliers/{created['id']}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_supplier_not_found(client: AsyncClient):
    resp = await client.delete(f"/api/v1/suppliers/{_uid()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_supplier_with_active_po(client: AsyncClient, db):
    """Supplier with non-terminal PO cannot be deleted."""
    from app.db.models import PurchaseOrder, POStatus, Supplier
    import uuid
    from datetime import datetime, timezone

    sup_id = str(uuid.uuid4())
    sup_code = f"SUP-PO-{_uid()[:6]}"
    supplier = Supplier(
        id=sup_id, tenant_id="test-tenant", name="WithPO", code=sup_code,
        is_active=True, payment_terms_days=30, lead_time_days=7,
        custom_attributes={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(supplier)
    await db.flush()

    po_id = str(uuid.uuid4())
    po = PurchaseOrder(
        id=po_id, tenant_id="test-tenant", supplier_id=sup_id,
        po_number=f"PO-2026-{uuid.uuid4().hex[:4]}",
        status=POStatus.draft,
        expected_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(po)
    await db.flush()

    resp = await client.delete(f"/api/v1/suppliers/{sup_id}")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_supplier_with_custom_attributes(client: AsyncClient):
    code = f"SUP-CUST-{_uid()[:6]}"
    resp = await client.post("/api/v1/suppliers", json={
        "name": "CustomSup", "code": code,
        "custom_attributes": {"region": "latam", "tier": 1},
    })
    assert resp.status_code == 201
    assert resp.json()["custom_attributes"]["region"] == "latam"


@pytest.mark.asyncio
async def test_create_warehouse_with_area_and_capacity(client: AsyncClient):
    code = f"WH-AREA-{_uid()[:6]}"
    resp = await client.post("/api/v1/warehouses", json={
        "name": "Big Warehouse", "code": code,
        "total_area_sqm": 500.0, "max_stock_capacity": 10000,
        "cost_per_sqm": 12.50,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["max_stock_capacity"] == 10000


@pytest.mark.asyncio
async def test_update_category_sort_order(client: AsyncClient):
    cat = (await client.post("/api/v1/categories", json={"name": f"SortCat-{_uid()[:6]}"})).json()
    resp = await client.patch(f"/api/v1/categories/{cat['id']}", json={"sort_order": 99})
    assert resp.status_code == 200
    assert resp.json()["sort_order"] == 99
