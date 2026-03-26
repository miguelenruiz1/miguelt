"""Deep tests for product endpoints — filters, image upload/delete, pricing,
cost history, purchase documents, delete constraints, SKU conflict on update."""
import io
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Product,
    PurchaseOrder,
    PurchaseOrderLine,
    RecipeComponent,
    EntityRecipe,
    StockLevel,
    StockMovement,
    Supplier,
    Warehouse,
    ProductCostHistory,
)
from app.db.models.production import StockLayer


def _uid() -> str:
    return str(uuid.uuid4())


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _create_product(client: AsyncClient, sku: str, **extra) -> dict:
    payload = {"name": f"Product {sku}", "sku": sku, "unit_of_measure": "un", **extra}
    resp = await client.post("/api/v1/products", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_warehouse(client: AsyncClient, code: str) -> str:
    resp = await client.post("/api/v1/warehouses", json={
        "name": f"WH-{code}", "code": code, "type": "main",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_supplier(db: AsyncSession, name: str, code: str) -> str:
    sid = _uid()
    db.add(Supplier(id=sid, tenant_id="test-tenant", name=name, code=code, is_active=True))
    await db.flush()
    return sid


async def _add_movement(db: AsyncSession, product_id: str, warehouse_id: str):
    """Insert a stock movement directly so the product is considered 'has_movements'."""
    mid = _uid()
    db.add(StockMovement(
        id=mid, tenant_id="test-tenant", product_id=product_id,
        to_warehouse_id=warehouse_id, movement_type="purchase",
        quantity=10, reference="TEST-MOV",
    ))
    await db.flush()


# ══════════════════════════════════════════════════════════════════════════════
# 1. LIST PRODUCTS — filters
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_filter_by_product_type(client: AsyncClient):
    """Filter products by product_type_id."""
    tr = await client.post("/api/v1/config/product-types", json={
        "name": "Electronics-LF", "slug": "electronics-lf",
    })
    type_id = tr.json()["id"]

    p1 = await _create_product(client, "PD-LFT-001", product_type_id=type_id)
    await _create_product(client, "PD-LFT-002")  # no type

    resp = await client.get("/api/v1/products", params={"product_type_id": type_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    ids = [i["id"] for i in data["items"]]
    assert p1["id"] in ids


@pytest.mark.asyncio
async def test_list_filter_is_active_false(client: AsyncClient):
    """Filter by is_active=false returns deactivated products."""
    p = await _create_product(client, "PD-ACTF-001")
    # deactivate
    await client.patch(f"/api/v1/products/{p['id']}", json={"is_active": False})

    resp = await client.get("/api/v1/products", params={"is_active": "false"})
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert p["id"] in ids


@pytest.mark.asyncio
async def test_list_filter_search(client: AsyncClient):
    """Search by name substring."""
    await _create_product(client, "PD-SRC-001", name="Jabón Artesanal Lavanda")
    resp = await client.get("/api/v1/products", params={"search": "Lavanda"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_list_filter_search_by_sku(client: AsyncClient):
    """Search also matches SKU."""
    await _create_product(client, "XYZUNIQUE-001")
    resp = await client.get("/api/v1/products", params={"search": "XYZUNIQUE"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_list_stock_status_out(client: AsyncClient, db: AsyncSession):
    """stock_status=out returns products with threshold but no stock."""
    p = await _create_product(client, "PD-OUT-001", min_stock_level=5, reorder_point=10)
    # No StockLevel rows → product is "out of stock"
    resp = await client.get("/api/v1/products", params={"stock_status": "out"})
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert p["id"] in ids


@pytest.mark.asyncio
async def test_list_stock_status_low(client: AsyncClient, db: AsyncSession):
    """stock_status=low returns products with qty <= threshold."""
    wid = await _create_warehouse(client, "WH-LOW-01")
    p = await _create_product(client, "PD-LOW-001", min_stock_level=50, reorder_point=100)
    # Add a StockLevel with qty_on_hand = 5 (below threshold)
    db.add(StockLevel(
        id=_uid(), tenant_id="test-tenant", product_id=p["id"],
        warehouse_id=wid, qty_on_hand=5, qty_reserved=0,
        reorder_point=100,
    ))
    await db.flush()

    resp = await client.get("/api/v1/products", params={"stock_status": "low"})
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert p["id"] in ids


# ══════════════════════════════════════════════════════════════════════════════
# 2. GET /products/{id} — 404
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/products/{_uid()}")
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 3. PATCH /products/{id} — SKU conflict + locked fields
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_update_sku_conflict(client: AsyncClient):
    """Updating SKU to one already taken returns conflict."""
    await _create_product(client, "PD-SKUC-001")
    p2 = await _create_product(client, "PD-SKUC-002")

    resp = await client.patch(f"/api/v1/products/{p2['id']}", json={"sku": "PD-SKUC-001"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_locked_field_with_movements(client: AsyncClient, db: AsyncSession):
    """Cannot change SKU once product has movements."""
    wid = await _create_warehouse(client, "WH-LCK-01")
    p = await _create_product(client, "PD-LOCK-001")
    await _add_movement(db, p["id"], wid)

    resp = await client.patch(f"/api/v1/products/{p['id']}", json={"sku": "PD-LOCK-NEW"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_locked_uom_with_movements(client: AsyncClient, db: AsyncSession):
    """Cannot change unit_of_measure once product has movements."""
    wid = await _create_warehouse(client, "WH-LCKU-01")
    p = await _create_product(client, "PD-LOCKU-001")
    await _add_movement(db, p["id"], wid)

    resp = await client.patch(f"/api/v1/products/{p['id']}", json={"unit_of_measure": "kg"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_non_locked_field_with_movements(client: AsyncClient, db: AsyncSession):
    """Can still change name even with movements."""
    wid = await _create_warehouse(client, "WH-NLK-01")
    p = await _create_product(client, "PD-NLCK-001")
    await _add_movement(db, p["id"], wid)

    resp = await client.patch(f"/api/v1/products/{p['id']}", json={"name": "Renamed OK"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed OK"


# ══════════════════════════════════════════════════════════════════════════════
# 4. DELETE /products/{id} — constraints
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_delete_product_404(client: AsyncClient):
    resp = await client.delete(f"/api/v1/products/{_uid()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_product_with_active_po(client: AsyncClient, db: AsyncSession):
    """Cannot delete a product referenced in an active PO."""
    p = await _create_product(client, "PD-DELPO-001")
    wid = await _create_warehouse(client, "WH-DPO-01")
    sup_id = await _create_supplier(db, "Sup-DELPO", "SDPO-01")

    po_id = _uid()
    db.add(PurchaseOrder(
        id=po_id, tenant_id="test-tenant", po_number="PO-2026-9901",
        supplier_id=sup_id, warehouse_id=wid, status="draft",
    ))
    await db.flush()
    db.add(PurchaseOrderLine(
        id=_uid(), po_id=po_id, product_id=p["id"],
        qty_ordered=10, unit_cost=100, line_total=1000, tenant_id="test-tenant",
    ))
    await db.flush()

    resp = await client.delete(f"/api/v1/products/{p['id']}")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_product_with_recipe(client: AsyncClient, db: AsyncSession):
    """Cannot delete a product that is a component in a recipe."""
    output_prod = await _create_product(client, "PD-DELRC-OUT")
    component_prod = await _create_product(client, "PD-DELRC-CMP")

    recipe_id = _uid()
    db.add(EntityRecipe(
        id=recipe_id, tenant_id="test-tenant", name="Test Recipe",
        output_entity_id=output_prod["id"], output_quantity=1,
    ))
    await db.flush()
    db.add(RecipeComponent(
        id=_uid(), tenant_id="test-tenant", recipe_id=recipe_id,
        component_entity_id=component_prod["id"], quantity_required=2,
    ))
    await db.flush()

    resp = await client.delete(f"/api/v1/products/{component_prod['id']}")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_product_success(client: AsyncClient):
    """Delete product with no constraints succeeds (soft delete)."""
    p = await _create_product(client, "PD-DELOK-001")
    resp = await client.delete(f"/api/v1/products/{p['id']}")
    assert resp.status_code == 204


# ══════════════════════════════════════════════════════════════════════════════
# 5. POST /products/{id}/images — upload
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_upload_image(client: AsyncClient, tmp_path, monkeypatch):
    """Upload a JPEG image to a product."""
    p = await _create_product(client, "PD-IMG-001")

    # Point UPLOAD_DIR to tmp_path so disk write succeeds
    from app.core.settings import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    files = {"file": ("test.jpg", io.BytesIO(b"fake-image-data"), "image/jpeg")}
    resp = await client.post(f"/api/v1/products/{p['id']}/images", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["images"]) == 1
    assert data["images"][0].startswith("/uploads/products/")


@pytest.mark.asyncio
async def test_upload_image_unsupported_format(client: AsyncClient):
    """Reject non-image file types."""
    p = await _create_product(client, "PD-IMG-002")
    files = {"file": ("doc.pdf", io.BytesIO(b"fake-pdf"), "application/pdf")}
    resp = await client.post(f"/api/v1/products/{p['id']}/images", files=files)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_image_too_large(client: AsyncClient, monkeypatch):
    """Reject images larger than MAX_IMAGE_SIZE."""
    p = await _create_product(client, "PD-IMG-003")

    from app.core.settings import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "MAX_IMAGE_SIZE", 100)  # 100 bytes limit

    files = {"file": ("big.jpg", io.BytesIO(b"x" * 200), "image/jpeg")}
    resp = await client.post(f"/api/v1/products/{p['id']}/images", files=files)
    assert resp.status_code == 413


# ══════════════════════════════════════════════════════════════════════════════
# 6. DELETE /products/{id}/images
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_delete_image(client: AsyncClient, tmp_path, monkeypatch):
    """Upload then delete an image."""
    p = await _create_product(client, "PD-IMGDEL-001")

    from app.core.settings import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    files = {"file": ("test.png", io.BytesIO(b"fake-png"), "image/png")}
    upload_resp = await client.post(f"/api/v1/products/{p['id']}/images", files=files)
    assert upload_resp.status_code == 200
    image_url = upload_resp.json()["images"][0]

    resp = await client.delete(
        f"/api/v1/products/{p['id']}/images",
        params={"image_url": image_url},
    )
    assert resp.status_code == 200
    assert image_url not in resp.json()["images"]


@pytest.mark.asyncio
async def test_delete_image_invalid_url(client: AsyncClient, monkeypatch):
    """Reject image_url with invalid filename pattern."""
    p = await _create_product(client, "PD-IMGDELI-001")

    from app.core.settings import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", "/tmp/test-uploads")

    resp = await client.delete(
        f"/api/v1/products/{p['id']}/images",
        params={"image_url": "/uploads/products/../../etc/passwd"},
    )
    assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# 7. GET /products/{id}/customer-prices
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_customer_prices_empty(client: AsyncClient):
    """No customer prices for a new product returns empty list."""
    p = await _create_product(client, "PD-CPRC-001")
    resp = await client.get(f"/api/v1/products/{p['id']}/customer-prices")
    assert resp.status_code == 200
    assert resp.json() == []


# ══════════════════════════════════════════════════════════════════════════════
# 8. GET /products/{id}/cost-history
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cost_history_empty(client: AsyncClient):
    """No cost history for new product returns empty list."""
    p = await _create_product(client, "PD-CHIST-001")
    resp = await client.get(f"/api/v1/products/{p['id']}/cost-history")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_cost_history_with_records(client: AsyncClient, db: AsyncSession):
    """Cost history returns records when they exist."""
    p = await _create_product(client, "PD-CHIST-002")
    wid = await _create_warehouse(client, "WH-CH-01")
    sup_id = await _create_supplier(db, "Sup-CH", "SCH-01")

    # Create PO + line so FK references work
    po_id = _uid()
    line_id = _uid()
    db.add(PurchaseOrder(
        id=po_id, tenant_id="test-tenant", po_number="PO-2026-8801",
        supplier_id=sup_id, warehouse_id=wid, status="received",
    ))
    await db.flush()
    db.add(PurchaseOrderLine(
        id=line_id, po_id=po_id, product_id=p["id"],
        qty_ordered=100, unit_cost=5000, line_total=500000, tenant_id="test-tenant",
    ))
    await db.flush()

    db.add(ProductCostHistory(
        id=_uid(), tenant_id="test-tenant", product_id=p["id"],
        purchase_order_id=po_id, purchase_order_line_id=line_id,
        supplier_id=sup_id, supplier_name="Sup-CH",
        uom_purchased="un", qty_purchased=100, qty_in_base_uom=100,
        unit_cost_purchased=5000, unit_cost_base_uom=5000, total_cost=500000,
    ))
    await db.flush()

    resp = await client.get(f"/api/v1/products/{p['id']}/cost-history")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert items[0]["supplier_name"] == "Sup-CH"


@pytest.mark.asyncio
async def test_cost_history_limit(client: AsyncClient, db: AsyncSession):
    """Cost history respects the limit parameter."""
    p = await _create_product(client, "PD-CHIST-003")
    resp = await client.get(f"/api/v1/products/{p['id']}/cost-history", params={"limit": 1})
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 9. GET /products/{id}/pricing
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pricing_empty_product(client: AsyncClient):
    """Pricing endpoint returns null costs for a new product."""
    p = await _create_product(client, "PD-PRIC-001")
    resp = await client.get(f"/api/v1/products/{p['id']}/pricing")
    assert resp.status_code == 200
    data = resp.json()
    assert "last_purchase_cost" in data
    assert "current_avg_cost" in data
    assert "cost_history" in data
    assert data["current_avg_cost"] is None
    assert data["cost_history"] == []


@pytest.mark.asyncio
async def test_pricing_with_stock_layers(client: AsyncClient, db: AsyncSession):
    """Pricing returns avg cost when stock layers exist."""
    p = await _create_product(client, "PD-PRIC-002")
    wid = await _create_warehouse(client, "WH-PRC-01")

    # Create stock layers
    db.add(StockLayer(
        id=_uid(), tenant_id="test-tenant", entity_id=p["id"],
        warehouse_id=wid, quantity_initial=100, quantity_remaining=100,
        unit_cost=5000,
    ))
    db.add(StockLayer(
        id=_uid(), tenant_id="test-tenant", entity_id=p["id"],
        warehouse_id=wid, quantity_initial=50, quantity_remaining=50,
        unit_cost=6000,
    ))
    await db.flush()

    resp = await client.get(f"/api/v1/products/{p['id']}/pricing")
    assert resp.status_code == 200
    data = resp.json()
    # Weighted average: (100*5000 + 50*6000) / 150 = 5333.33...
    assert data["current_avg_cost"] is not None
    assert abs(data["current_avg_cost"] - 5333.33) < 1


# ══════════════════════════════════════════════════════════════════════════════
# 10. POST /products/{id}/recalculate-prices
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_recalculate_prices(client: AsyncClient):
    """Recalculate prices endpoint returns product data."""
    p = await _create_product(client, "PD-RECALC-001")
    resp = await client.post(f"/api/v1/products/{p['id']}/recalculate-prices")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == p["id"]


@pytest.mark.asyncio
async def test_recalculate_prices_not_found(client: AsyncClient):
    resp = await client.post(f"/api/v1/products/{_uid()}/recalculate-prices")
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 11. POST /products/fix-zero-costs
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_fix_zero_costs_no_products(client: AsyncClient):
    """fix-zero-costs with no zero-cost products reports nothing fixed."""
    resp = await client.post("/api/v1/products/fix-zero-costs")
    assert resp.status_code == 200
    data = resp.json()
    assert "scanned" in data
    assert "fixed" in data


@pytest.mark.asyncio
async def test_fix_zero_costs_patches_from_history(client: AsyncClient, db: AsyncSession):
    """fix-zero-costs patches a product with null cost from cost history."""
    p = await _create_product(client, "PD-FIX-001")
    wid = await _create_warehouse(client, "WH-FIX-01")
    sup_id = await _create_supplier(db, "Sup-FIX", "SFIX-01")

    # Ensure product has null last_purchase_cost (default)
    pid = p["id"]

    # Create PO + line for FK
    po_id = _uid()
    line_id = _uid()
    db.add(PurchaseOrder(
        id=po_id, tenant_id="test-tenant", po_number="PO-2026-7701",
        supplier_id=sup_id, warehouse_id=wid, status="received",
    ))
    await db.flush()
    db.add(PurchaseOrderLine(
        id=line_id, po_id=po_id, product_id=pid,
        qty_ordered=50, unit_cost=3000, line_total=150000, tenant_id="test-tenant",
    ))
    await db.flush()

    # Add cost history record
    db.add(ProductCostHistory(
        id=_uid(), tenant_id="test-tenant", product_id=pid,
        purchase_order_id=po_id, purchase_order_line_id=line_id,
        supplier_id=sup_id, supplier_name="Sup-FIX",
        uom_purchased="un", qty_purchased=50, qty_in_base_uom=50,
        unit_cost_purchased=3000, unit_cost_base_uom=3000, total_cost=150000,
    ))
    await db.flush()

    resp = await client.post("/api/v1/products/fix-zero-costs")
    assert resp.status_code == 200
    data = resp.json()
    # The product we just created with null cost should be found and fixed
    fixed_skus = [fp["sku"] for fp in data["products"]]
    assert "PD-FIX-001" in fixed_skus


# ══════════════════════════════════════════════════════════════════════════════
# 12. GET /products/{id}/purchase-documents
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_purchase_documents_empty(client: AsyncClient):
    """No purchase documents for a new product."""
    p = await _create_product(client, "PD-PDOC-001")
    resp = await client.get(f"/api/v1/products/{p['id']}/purchase-documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["documents"] == []
    assert data["cost_records"] == []


@pytest.mark.asyncio
async def test_purchase_documents_with_records(client: AsyncClient, db: AsyncSession):
    """Purchase documents are returned when cost history exists."""
    p = await _create_product(client, "PD-PDOC-002")
    wid = await _create_warehouse(client, "WH-PD-01")
    sup_id = await _create_supplier(db, "Sup-PD", "SPD-01")

    po_id = _uid()
    line_id = _uid()
    db.add(PurchaseOrder(
        id=po_id, tenant_id="test-tenant", po_number="PO-2026-6601",
        supplier_id=sup_id, warehouse_id=wid, status="received",
        attachments=[{"name": "invoice.pdf", "url": "/uploads/invoice.pdf", "type": "invoice"}],
        supplier_invoice_number="INV-001",
    ))
    await db.flush()
    db.add(PurchaseOrderLine(
        id=line_id, po_id=po_id, product_id=p["id"],
        qty_ordered=20, unit_cost=1000, line_total=20000, tenant_id="test-tenant",
    ))
    await db.flush()
    db.add(ProductCostHistory(
        id=_uid(), tenant_id="test-tenant", product_id=p["id"],
        purchase_order_id=po_id, purchase_order_line_id=line_id,
        supplier_id=sup_id, supplier_name="Sup-PD",
        uom_purchased="un", qty_purchased=20, qty_in_base_uom=20,
        unit_cost_purchased=1000, unit_cost_base_uom=1000, total_cost=20000,
    ))
    await db.flush()

    resp = await client.get(f"/api/v1/products/{p['id']}/purchase-documents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["cost_records"]) >= 1
    assert data["cost_records"][0]["supplier_name"] == "Sup-PD"
    assert len(data["documents"]) >= 1
    assert data["documents"][0]["file_name"] == "invoice.pdf"


# ══════════════════════════════════════════════════════════════════════════════
# Extra coverage — product type defaults, has_movements flag, margins update
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_product_has_movements_flag(client: AsyncClient, db: AsyncSession):
    """Product detail includes has_movements boolean."""
    wid = await _create_warehouse(client, "WH-HM-01")
    p = await _create_product(client, "PD-HM-001")

    resp = await client.get(f"/api/v1/products/{p['id']}")
    assert resp.json()["has_movements"] is False

    await _add_movement(db, p["id"], wid)

    resp = await client.get(f"/api/v1/products/{p['id']}")
    assert resp.json()["has_movements"] is True


@pytest.mark.asyncio
async def test_update_margins(client: AsyncClient):
    """PATCH /products/{id}/margins updates margin fields."""
    p = await _create_product(client, "PD-MARG-001")
    resp = await client.patch(
        f"/api/v1/products/{p['id']}/margins",
        params={"margin_target": 40.0, "margin_minimum": 20.0},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_pagination(client: AsyncClient):
    """List respects offset and limit."""
    for i in range(3):
        await _create_product(client, f"PD-PAG-{i:03d}")

    resp = await client.get("/api/v1/products", params={"offset": 0, "limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2
    assert data["limit"] == 2
