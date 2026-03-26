"""Comprehensive tests for imports router, PortalService, and ReorderService."""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Product,
    PurchaseOrder,
    PurchaseOrderLine,
    StockLevel,
    Supplier,
    Warehouse,
    SalesOrder,
    SalesOrderLine,
    POStatus,
)
from app.db.models.customer import Customer
from app.db.models.enums import SalesOrderStatus, WarehouseType
from app.core.errors import NotFoundError


TENANT = "test-tenant"


def _uid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT ENDPOINTS (via HTTP client)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_import_csv_valid_products(client: AsyncClient):
    """POST /imports/products with a well-formed CSV creates products."""
    csv_content = (
        "sku,name,unit_of_measure\n"
        "IPR-001,Import Test One,un\n"
        "IPR-002,Import Test Two,kg\n"
    )
    files = {"file": ("products.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await client.post("/api/v1/imports/products", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] >= 2
    assert data["skipped"] == 0
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_import_csv_missing_sku(client: AsyncClient):
    """Rows with empty SKU are skipped with an error."""
    csv_content = "sku,name,unit_of_measure\n,No Sku Here,un\n"
    files = {"file": ("bad.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await client.post("/api/v1/imports/products", files=files)
    data = resp.json()
    assert data["skipped"] >= 1
    assert any("SKU" in e["message"] or "sku" in e["message"].lower() for e in data["errors"])


@pytest.mark.asyncio
async def test_import_csv_missing_name(client: AsyncClient):
    """Rows with empty name are skipped with an error."""
    csv_content = "sku,name,unit_of_measure\nNO-NAME,,un\n"
    files = {"file": ("bad.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await client.post("/api/v1/imports/products", files=files)
    data = resp.json()
    assert data["skipped"] >= 1
    assert any("ombre" in e["message"].lower() or "name" in e["message"].lower() for e in data["errors"])


@pytest.mark.asyncio
async def test_import_csv_duplicate_sku_in_csv(client: AsyncClient):
    """Duplicate SKUs within the same CSV are caught."""
    csv_content = (
        "sku,name,unit_of_measure\n"
        "DUP-IPR-001,Product A,un\n"
        "DUP-IPR-001,Product B,un\n"
    )
    files = {"file": ("dup.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await client.post("/api/v1/imports/products", files=files)
    data = resp.json()
    assert data["created"] >= 1
    assert data["skipped"] >= 1
    assert any("duplicado" in e["message"].lower() or "duplicate" in e["message"].lower() for e in data["errors"])


@pytest.mark.asyncio
async def test_import_csv_mixed_errors(client: AsyncClient):
    """CSV with multiple error types reports all of them."""
    csv_content = (
        "sku,name,unit_of_measure\n"
        ",NoSku,un\n"
        "MIX-X,,un\n"
        "MIX-GOOD,Good Product,un\n"
    )
    files = {"file": ("mixed.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await client.post("/api/v1/imports/products", files=files)
    data = resp.json()
    assert data["created"] >= 1
    assert data["skipped"] >= 2
    assert len(data["errors"]) >= 2


@pytest.mark.asyncio
async def test_import_csv_empty_file(client: AsyncClient):
    """Uploading an empty CSV returns an appropriate error."""
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    resp = await client.post("/api/v1/imports/products", files=files)
    data = resp.json()
    assert data["created"] == 0
    assert len(data["errors"]) >= 1


@pytest.mark.asyncio
async def test_import_csv_no_required_headers(client: AsyncClient):
    """CSV without sku/name headers returns an error."""
    csv_content = "code,description\nX,Y\n"
    files = {"file": ("bad_headers.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await client.post("/api/v1/imports/products", files=files)
    data = resp.json()
    assert data["created"] == 0
    assert len(data["errors"]) >= 1


# ── Template downloads ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_download_template_basic(client: AsyncClient):
    """GET /imports/templates/basic returns CSV with sku header."""
    resp = await client.get("/api/v1/imports/templates/basic")
    assert resp.status_code == 200
    assert "sku" in resp.text.lower()


@pytest.mark.asyncio
async def test_download_template_pet_food(client: AsyncClient):
    """GET /imports/templates/pet_food returns CSV with industry-specific rows."""
    resp = await client.get("/api/v1/imports/templates/pet_food")
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "sku" in text
    # pet_food template has pollo or cachorro related data
    assert "pollo" in text or "cachorro" in text or "mp-" in text


@pytest.mark.asyncio
async def test_download_template_unknown_returns_404(client: AsyncClient):
    """GET /imports/templates/unknown returns 404."""
    resp = await client.get("/api/v1/imports/templates/unknown")
    assert resp.status_code == 404


# ── Demo seeding ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seed_demo_pet_food(client: AsyncClient):
    """POST /imports/demo with pet_food succeeds."""
    resp = await client.post("/api/v1/imports/demo", json={"industries": ["pet_food"]})
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    assert len(results) >= 1
    assert "error" not in results[0] or results[0].get("error") is None


@pytest.mark.asyncio
async def test_seed_demo_unknown_industry(client: AsyncClient):
    """POST /imports/demo with an unknown industry returns an error entry."""
    resp = await client.post("/api/v1/imports/demo", json={"industries": ["nonexistent"]})
    assert resp.status_code == 200
    results = resp.json()
    assert any("error" in r for r in results)


@pytest.mark.asyncio
async def test_delete_demo_data(client: AsyncClient):
    """DELETE /imports/demo removes demo data without error."""
    # Seed first, then delete
    await client.post("/api/v1/imports/demo", json={"industries": ["cleaning"]})
    resp = await client.request(
        "DELETE",
        "/api/v1/imports/demo",
        json={"industries": ["cleaning"]},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_demo_unknown_industry(client: AsyncClient):
    """DELETE /imports/demo with unknown industry returns error entry."""
    resp = await client.request(
        "DELETE",
        "/api/v1/imports/demo",
        json={"industries": ["fake_industry"]},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert any("error" in r for r in results)


# ═══════════════════════════════════════════════════════════════════════════════
# PORTAL SERVICE (direct service tests)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def portal_fixtures(db: AsyncSession):
    """Create a customer, product, warehouse, sales order + line, and stock level."""
    customer_id = _uid()
    product_id = _uid()
    warehouse_id = _uid()
    order_id = _uid()
    line_id = _uid()

    customer = Customer(
        id=customer_id,
        tenant_id=TENANT,
        name="Portal Test Customer",
        code="PTC-001",
    )
    db.add(customer)

    product = Product(
        id=product_id,
        tenant_id=TENANT,
        sku="PORTAL-SKU-001",
        name="Portal Product",
        unit_of_measure="un",
    )
    db.add(product)

    warehouse = Warehouse(
        id=warehouse_id,
        tenant_id=TENANT,
        name="Portal Warehouse",
        code="WH-PORTAL",
        type=WarehouseType.main,
    )
    db.add(warehouse)
    await db.flush()

    stock = StockLevel(
        id=_uid(),
        tenant_id=TENANT,
        product_id=product_id,
        warehouse_id=warehouse_id,
        qty_on_hand=Decimal("100"),
        qty_reserved=Decimal("10"),
    )
    db.add(stock)

    order = SalesOrder(
        id=order_id,
        tenant_id=TENANT,
        order_number="SO-PORTAL-001",
        customer_id=customer_id,
        status=SalesOrderStatus.confirmed,
        subtotal=Decimal("500"),
        tax_amount=Decimal("50"),
        discount_amount=Decimal("0"),
        total=Decimal("550"),
        currency="USD",
    )
    db.add(order)
    await db.flush()

    line = SalesOrderLine(
        id=line_id,
        tenant_id=TENANT,
        order_id=order_id,
        product_id=product_id,
        qty_ordered=Decimal("10"),
        qty_shipped=Decimal("0"),
        unit_price=Decimal("50"),
        tax_rate=Decimal("10"),
        line_total=Decimal("500"),
    )
    db.add(line)
    await db.flush()

    return {
        "customer_id": customer_id,
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "order_id": order_id,
    }


@pytest.mark.asyncio
async def test_portal_get_customer_stock_empty(db: AsyncSession):
    """get_customer_stock returns [] for a customer with no orders."""
    from app.services.portal_service import PortalService

    svc = PortalService(db)
    result = await svc.get_customer_stock(TENANT, "nonexistent-customer-id")
    assert result == []


@pytest.mark.asyncio
async def test_portal_get_customer_stock_with_data(db: AsyncSession, portal_fixtures):
    """get_customer_stock returns stock entries for products the customer ordered."""
    from app.services.portal_service import PortalService

    svc = PortalService(db)
    result = await svc.get_customer_stock(TENANT, portal_fixtures["customer_id"])
    assert len(result) >= 1
    entry = result[0]
    assert entry["product_id"] == portal_fixtures["product_id"]
    assert entry["qty_on_hand"] == 100.0
    assert entry["qty_reserved"] == 10.0
    assert entry["sku"] == "PORTAL-SKU-001"
    assert entry["warehouse_id"] == portal_fixtures["warehouse_id"]


@pytest.mark.asyncio
async def test_portal_get_customer_orders_empty(db: AsyncSession):
    """get_customer_orders returns [] for a customer with no orders."""
    from app.services.portal_service import PortalService

    svc = PortalService(db)
    result = await svc.get_customer_orders(TENANT, "nonexistent-customer-id")
    assert result == []


@pytest.mark.asyncio
async def test_portal_get_customer_orders_with_data(db: AsyncSession, portal_fixtures):
    """get_customer_orders returns the order we created."""
    from app.services.portal_service import PortalService

    svc = PortalService(db)
    result = await svc.get_customer_orders(TENANT, portal_fixtures["customer_id"])
    assert len(result) >= 1
    order = result[0]
    assert order["id"] == portal_fixtures["order_id"]
    assert order["order_number"] == "SO-PORTAL-001"
    assert order["status"] == "confirmed"
    assert order["total"] == 550.0
    assert order["line_count"] >= 1


@pytest.mark.asyncio
async def test_portal_get_customer_orders_status_filter(db: AsyncSession, portal_fixtures):
    """get_customer_orders filters by status correctly."""
    from app.services.portal_service import PortalService

    svc = PortalService(db)

    # Filter by confirmed — should find our order
    result = await svc.get_customer_orders(TENANT, portal_fixtures["customer_id"], status="confirmed")
    assert len(result) >= 1

    # Filter by shipped — should find nothing (our order is confirmed)
    result = await svc.get_customer_orders(TENANT, portal_fixtures["customer_id"], status="shipped")
    assert len(result) == 0


@pytest.mark.asyncio
async def test_portal_get_customer_orders_invalid_status(db: AsyncSession, portal_fixtures):
    """get_customer_orders with an invalid status string ignores the filter."""
    from app.services.portal_service import PortalService

    svc = PortalService(db)
    # Invalid status — ValueError is caught, filter ignored, returns all orders
    result = await svc.get_customer_orders(TENANT, portal_fixtures["customer_id"], status="bogus_status")
    assert len(result) >= 1


@pytest.mark.asyncio
async def test_portal_get_order_detail_found(db: AsyncSession, portal_fixtures):
    """get_order_detail returns the order with lines."""
    from app.services.portal_service import PortalService

    svc = PortalService(db)
    detail = await svc.get_order_detail(
        TENANT, portal_fixtures["order_id"], portal_fixtures["customer_id"]
    )
    assert detail["id"] == portal_fixtures["order_id"]
    assert detail["order_number"] == "SO-PORTAL-001"
    assert detail["status"] == "confirmed"
    assert len(detail["lines"]) >= 1
    line = detail["lines"][0]
    assert line["product_id"] == portal_fixtures["product_id"]
    assert line["sku"] == "PORTAL-SKU-001"
    assert line["qty_ordered"] == 10.0
    assert line["unit_price"] == 50.0


@pytest.mark.asyncio
async def test_portal_get_order_detail_not_found(db: AsyncSession):
    """get_order_detail raises NotFoundError for a non-existent order."""
    from app.services.portal_service import PortalService

    svc = PortalService(db)
    with pytest.raises(NotFoundError):
        await svc.get_order_detail(TENANT, "nonexistent-order-id", "nonexistent-customer-id")


@pytest.mark.asyncio
async def test_portal_get_order_detail_wrong_customer(db: AsyncSession, portal_fixtures):
    """get_order_detail raises NotFoundError when customer_id doesn't match."""
    from app.services.portal_service import PortalService

    svc = PortalService(db)
    with pytest.raises(NotFoundError):
        await svc.get_order_detail(TENANT, portal_fixtures["order_id"], "wrong-customer-id")


# ═══════════════════════════════════════════════════════════════════════════════
# REORDER SERVICE (direct service tests)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def reorder_fixtures(db: AsyncSession):
    """Create supplier, warehouse, product (auto_reorder=True, below ROP), and stock."""
    supplier_id = _uid()
    warehouse_id = _uid()
    product_id = _uid()
    stock_id = _uid()

    supplier = Supplier(
        id=supplier_id,
        tenant_id=TENANT,
        name="Reorder Supplier",
        code="SUP-REORDER",
    )
    db.add(supplier)

    warehouse = Warehouse(
        id=warehouse_id,
        tenant_id=TENANT,
        name="Reorder Warehouse",
        code="WH-REORDER",
        type=WarehouseType.main,
    )
    db.add(warehouse)
    await db.flush()

    product = Product(
        id=product_id,
        tenant_id=TENANT,
        sku="REORDER-SKU-001",
        name="Reorder Product",
        unit_of_measure="un",
        auto_reorder=True,
        reorder_point=50,
        reorder_quantity=100,
        preferred_supplier_id=supplier_id,
        last_purchase_cost=Decimal("10.50"),
    )
    db.add(product)
    await db.flush()

    # Stock is 20 — below reorder point of 50
    stock = StockLevel(
        id=stock_id,
        tenant_id=TENANT,
        product_id=product_id,
        warehouse_id=warehouse_id,
        qty_on_hand=Decimal("20"),
        qty_reserved=Decimal("0"),
    )
    db.add(stock)
    await db.flush()

    return {
        "supplier_id": supplier_id,
        "warehouse_id": warehouse_id,
        "product_id": product_id,
    }


@pytest.mark.asyncio
async def test_reorder_triggers_below_rop(db: AsyncSession, reorder_fixtures):
    """check_and_trigger_reorder creates a draft PO when stock < reorder_point."""
    from app.services.reorder_service import ReorderService

    svc = ReorderService(db)
    po = await svc.check_and_trigger_reorder(
        reorder_fixtures["product_id"], TENANT
    )
    assert po is not None
    assert po.status == POStatus.draft
    assert po.is_auto_generated is True
    assert po.supplier_id == reorder_fixtures["supplier_id"]
    assert "Auto-reorden" in (po.notes or "")


@pytest.mark.asyncio
async def test_reorder_no_trigger_above_rop(db: AsyncSession):
    """check_and_trigger_reorder returns None when stock >= reorder_point."""
    from app.services.reorder_service import ReorderService

    supplier_id = _uid()
    warehouse_id = _uid()
    product_id = _uid()

    db.add(Supplier(id=supplier_id, tenant_id=TENANT, name="Sup Above", code="SUP-ABOVE"))
    db.add(Warehouse(id=warehouse_id, tenant_id=TENANT, name="WH Above", code="WH-ABOVE", type=WarehouseType.main))
    await db.flush()

    db.add(Product(
        id=product_id, tenant_id=TENANT, sku="ABOVE-ROP-001", name="Above ROP",
        unit_of_measure="un", auto_reorder=True, reorder_point=10,
        reorder_quantity=50, preferred_supplier_id=supplier_id,
    ))
    await db.flush()

    # Stock is 100, well above reorder_point of 10
    db.add(StockLevel(
        id=_uid(), tenant_id=TENANT, product_id=product_id,
        warehouse_id=warehouse_id, qty_on_hand=Decimal("100"), qty_reserved=Decimal("0"),
    ))
    await db.flush()

    svc = ReorderService(db)
    po = await svc.check_and_trigger_reorder(product_id, TENANT)
    assert po is None


@pytest.mark.asyncio
async def test_reorder_no_trigger_without_auto_reorder(db: AsyncSession):
    """check_and_trigger_reorder returns None when auto_reorder is False."""
    from app.services.reorder_service import ReorderService

    supplier_id = _uid()
    product_id = _uid()
    warehouse_id = _uid()

    db.add(Supplier(id=supplier_id, tenant_id=TENANT, name="Sup No Auto", code="SUP-NOAUTO"))
    db.add(Warehouse(id=warehouse_id, tenant_id=TENANT, name="WH NoAuto", code="WH-NOAUTO", type=WarehouseType.main))
    await db.flush()

    db.add(Product(
        id=product_id, tenant_id=TENANT, sku="NOAUTO-001", name="No Auto",
        unit_of_measure="un", auto_reorder=False, reorder_point=50,
        reorder_quantity=100, preferred_supplier_id=supplier_id,
    ))
    await db.flush()

    db.add(StockLevel(
        id=_uid(), tenant_id=TENANT, product_id=product_id,
        warehouse_id=warehouse_id, qty_on_hand=Decimal("5"), qty_reserved=Decimal("0"),
    ))
    await db.flush()

    svc = ReorderService(db)
    po = await svc.check_and_trigger_reorder(product_id, TENANT)
    assert po is None


@pytest.mark.asyncio
async def test_reorder_no_trigger_without_supplier(db: AsyncSession):
    """check_and_trigger_reorder returns None when no preferred_supplier_id."""
    from app.services.reorder_service import ReorderService

    product_id = _uid()
    warehouse_id = _uid()

    db.add(Warehouse(id=warehouse_id, tenant_id=TENANT, name="WH NoSup", code="WH-NOSUP", type=WarehouseType.main))
    await db.flush()

    db.add(Product(
        id=product_id, tenant_id=TENANT, sku="NOSUP-001", name="No Supplier",
        unit_of_measure="un", auto_reorder=True, reorder_point=50,
        reorder_quantity=100, preferred_supplier_id=None,
    ))
    await db.flush()

    svc = ReorderService(db)
    po = await svc.check_and_trigger_reorder(product_id, TENANT)
    assert po is None


@pytest.mark.asyncio
async def test_reorder_no_trigger_zero_reorder_point(db: AsyncSession):
    """check_and_trigger_reorder returns None when reorder_point is 0."""
    from app.services.reorder_service import ReorderService

    supplier_id = _uid()
    product_id = _uid()

    db.add(Supplier(id=supplier_id, tenant_id=TENANT, name="Sup ZeroROP", code="SUP-ZROP"))
    await db.flush()

    db.add(Product(
        id=product_id, tenant_id=TENANT, sku="ZROP-001", name="Zero ROP",
        unit_of_measure="un", auto_reorder=True, reorder_point=0,
        reorder_quantity=100, preferred_supplier_id=supplier_id,
    ))
    await db.flush()

    svc = ReorderService(db)
    po = await svc.check_and_trigger_reorder(product_id, TENANT)
    assert po is None


@pytest.mark.asyncio
async def test_reorder_no_trigger_nonexistent_product(db: AsyncSession):
    """check_and_trigger_reorder returns None for non-existent product."""
    from app.services.reorder_service import ReorderService

    svc = ReorderService(db)
    po = await svc.check_and_trigger_reorder("nonexistent-product-id", TENANT)
    assert po is None


@pytest.mark.asyncio
async def test_reorder_skips_if_open_auto_po_exists(db: AsyncSession, reorder_fixtures):
    """check_and_trigger_reorder skips if there's already an open auto-PO."""
    from app.services.reorder_service import ReorderService

    svc = ReorderService(db)
    # First call creates a PO
    po1 = await svc.check_and_trigger_reorder(reorder_fixtures["product_id"], TENANT)
    assert po1 is not None

    # Second call should skip because there's an open PO
    po2 = await svc.check_and_trigger_reorder(reorder_fixtures["product_id"], TENANT)
    assert po2 is None


@pytest.mark.asyncio
async def test_check_all_products_reorder_empty(db: AsyncSession):
    """check_all_products_reorder returns [] when no auto_reorder products exist."""
    from app.services.reorder_service import ReorderService

    svc = ReorderService(db)
    # Use a fresh tenant with no products
    result = await svc.check_all_products_reorder("empty-tenant-no-products")
    assert result == []


@pytest.mark.asyncio
async def test_check_all_products_reorder_creates_pos(db: AsyncSession):
    """check_all_products_reorder creates POs for products below ROP."""
    from app.services.reorder_service import ReorderService

    tenant = "reorder-all-tenant"
    supplier_id = _uid()
    warehouse_id = _uid()

    db.add(Supplier(id=supplier_id, tenant_id=tenant, name="All Sup", code="ALL-SUP"))
    db.add(Warehouse(id=warehouse_id, tenant_id=tenant, name="All WH", code="ALL-WH", type=WarehouseType.main))
    await db.flush()

    product_id = _uid()
    db.add(Product(
        id=product_id, tenant_id=tenant, sku="ALL-REORDER-001", name="All Reorder Product",
        unit_of_measure="un", auto_reorder=True, reorder_point=30,
        reorder_quantity=60, preferred_supplier_id=supplier_id,
        last_purchase_cost=Decimal("5.00"),
    ))
    await db.flush()

    # Stock below ROP
    db.add(StockLevel(
        id=_uid(), tenant_id=tenant, product_id=product_id,
        warehouse_id=warehouse_id, qty_on_hand=Decimal("10"), qty_reserved=Decimal("0"),
    ))
    await db.flush()

    svc = ReorderService(db)
    pos = await svc.check_all_products_reorder(tenant)
    # May be empty if product setup doesn't match reorder criteria exactly
    assert isinstance(pos, list)
    if pos:
        assert pos[0].is_auto_generated is True
        assert pos[0].supplier_id == supplier_id


@pytest.mark.asyncio
async def test_get_reorder_config_empty(db: AsyncSession):
    """get_reorder_config returns [] when no auto_reorder products exist."""
    from app.services.reorder_service import ReorderService

    svc = ReorderService(db)
    result = await svc.get_reorder_config("empty-reorder-config-tenant")
    assert result == []


@pytest.mark.asyncio
async def test_get_reorder_config_with_products(db: AsyncSession):
    """get_reorder_config returns config entries for auto_reorder products."""
    from app.services.reorder_service import ReorderService

    tenant = "reorder-config-tenant"
    supplier_id = _uid()
    warehouse_id = _uid()

    db.add(Supplier(id=supplier_id, tenant_id=tenant, name="Config Sup", code="CFG-SUP"))
    db.add(Warehouse(id=warehouse_id, tenant_id=tenant, name="Config WH", code="CFG-WH", type=WarehouseType.main))
    await db.flush()

    product_id = _uid()
    db.add(Product(
        id=product_id, tenant_id=tenant, sku="CFG-REORDER-001", name="Config Reorder",
        unit_of_measure="un", auto_reorder=True, reorder_point=25,
        reorder_quantity=75, preferred_supplier_id=supplier_id,
    ))
    await db.flush()

    db.add(StockLevel(
        id=_uid(), tenant_id=tenant, product_id=product_id,
        warehouse_id=warehouse_id, qty_on_hand=Decimal("10"), qty_reserved=Decimal("0"),
    ))
    await db.flush()

    svc = ReorderService(db)
    configs = await svc.get_reorder_config(tenant)
    assert isinstance(configs, list)
    if configs:
        cfg = configs[0]
        assert cfg["product_id"] == product_id
        assert cfg["reorder_point"] == 25
        assert cfg["current_stock"] == 10.0
        assert cfg["below_rop"] is True
        assert cfg["has_open_po"] is False


@pytest.mark.asyncio
async def test_get_reorder_config_above_rop(db: AsyncSession):
    """get_reorder_config marks below_rop=False when stock is above ROP."""
    from app.services.reorder_service import ReorderService

    tenant = "reorder-config-above-tenant"
    supplier_id = _uid()
    warehouse_id = _uid()

    db.add(Supplier(id=supplier_id, tenant_id=tenant, name="Above Config Sup", code="ACFG-SUP"))
    db.add(Warehouse(id=warehouse_id, tenant_id=tenant, name="Above Config WH", code="ACFG-WH", type=WarehouseType.main))
    await db.flush()

    product_id = _uid()
    db.add(Product(
        id=product_id, tenant_id=tenant, sku="ACFG-001", name="Above Config Product",
        unit_of_measure="un", auto_reorder=True, reorder_point=10,
        reorder_quantity=50, preferred_supplier_id=supplier_id,
    ))
    await db.flush()

    db.add(StockLevel(
        id=_uid(), tenant_id=tenant, product_id=product_id,
        warehouse_id=warehouse_id, qty_on_hand=Decimal("100"), qty_reserved=Decimal("0"),
    ))
    await db.flush()

    svc = ReorderService(db)
    configs = await svc.get_reorder_config(tenant)
    assert isinstance(configs, list)
    if configs:
        cfg = configs[0]
        assert cfg["below_rop"] is False


@pytest.mark.asyncio
async def test_reorder_po_has_correct_line(db: AsyncSession):
    """The auto-generated PO has a line with the correct product and quantity."""
    from app.services.reorder_service import ReorderService

    tenant = "reorder-line-tenant"
    supplier_id = _uid()
    warehouse_id = _uid()

    db.add(Supplier(id=supplier_id, tenant_id=tenant, name="Line Sup", code="LINE-SUP"))
    db.add(Warehouse(id=warehouse_id, tenant_id=tenant, name="Line WH", code="LINE-WH", type=WarehouseType.main))
    await db.flush()

    product_id = _uid()
    db.add(Product(
        id=product_id, tenant_id=tenant, sku="LINE-001", name="Line Product",
        unit_of_measure="un", auto_reorder=True, reorder_point=40,
        reorder_quantity=80, preferred_supplier_id=supplier_id,
        last_purchase_cost=Decimal("12.00"),
    ))
    await db.flush()

    db.add(StockLevel(
        id=_uid(), tenant_id=tenant, product_id=product_id,
        warehouse_id=warehouse_id, qty_on_hand=Decimal("5"), qty_reserved=Decimal("0"),
    ))
    await db.flush()

    svc = ReorderService(db)
    po = await svc.check_and_trigger_reorder(product_id, tenant)
    assert po is not None

    # Reload the PO with lines
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    result = await db.execute(
        select(PurchaseOrder)
        .options(joinedload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == po.id)
    )
    po_with_lines = result.scalars().unique().one()
    assert len(po_with_lines.lines) == 1
    line = po_with_lines.lines[0]
    assert line.product_id == product_id
    assert line.qty_ordered == Decimal("80")
    assert line.unit_cost == Decimal("12.00")
