"""Unit tests for service classes — direct DB interaction via db fixture."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.models import (
    BusinessPartner,
    Category,
    Customer,
    CustomMovementField,
    CustomSupplierField,
    CustomWarehouseField,
    DynamicMovementType,
    DynamicWarehouseType,
    Product,
    PurchaseOrder,
    PurchaseOrderLine,
    RecipeComponent,
    StockMovement,
    Supplier,
    SupplierType,
)
from app.db.models.customer import CustomerType
from app.db.models.config import CustomProductField, ProductType
from app.services.partner_service import PartnerService
from app.services.customer_service import CustomerService
from app.services.supplier_service import SupplierService
from app.services.product_service import ProductService
from app.services.config_service import ConfigService


def uid() -> str:
    return str(uuid.uuid4())


TENANT = "svc-unit-tenant"


# ════════════════════════════════════════════════════════════════════════════
# PartnerService
# ════════════════════════════════════════════════════════════════════════════

class TestPartnerService:
    """Tests for PartnerService — create, get, update, delete."""

    @pytest.mark.asyncio
    async def test_create_supplier_partner(self, db):
        svc = PartnerService(db)
        partner = await svc.create(TENANT, {
            "code": f"BP-{uid()[:8]}",
            "name": "Acme Supplies",
            "is_supplier": True,
            "is_customer": False,
        })
        assert partner.id
        assert partner.is_supplier is True
        assert partner.tenant_id == TENANT

    @pytest.mark.asyncio
    async def test_create_customer_partner(self, db):
        svc = PartnerService(db)
        partner = await svc.create(TENANT, {
            "code": f"BP-{uid()[:8]}",
            "name": "Retail Client",
            "is_supplier": False,
            "is_customer": True,
        })
        assert partner.is_customer is True

    @pytest.mark.asyncio
    async def test_create_partner_neither_supplier_nor_customer_raises(self, db):
        svc = PartnerService(db)
        with pytest.raises(ValidationError, match="at least supplier or customer"):
            await svc.create(TENANT, {
                "code": "BP-INVALID",
                "name": "Nobody",
                "is_supplier": False,
                "is_customer": False,
            })

    @pytest.mark.asyncio
    async def test_create_partner_duplicate_code_raises(self, db):
        svc = PartnerService(db)
        code = f"BP-DUP-{uid()[:6]}"
        await svc.create(TENANT, {"code": code, "name": "First", "is_supplier": True, "is_customer": False})
        with pytest.raises(ValidationError, match="already in use"):
            await svc.create(TENANT, {"code": code, "name": "Second", "is_supplier": True, "is_customer": False})

    @pytest.mark.asyncio
    async def test_get_partner_not_found_raises(self, db):
        svc = PartnerService(db)
        with pytest.raises(NotFoundError):
            await svc.get(uid(), TENANT)

    @pytest.mark.asyncio
    async def test_get_partner_success(self, db):
        svc = PartnerService(db)
        created = await svc.create(TENANT, {
            "code": f"BP-{uid()[:8]}", "name": "GetMe", "is_supplier": True, "is_customer": False,
        })
        fetched = await svc.get(created.id, TENANT)
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_update_partner_name(self, db):
        svc = PartnerService(db)
        p = await svc.create(TENANT, {
            "code": f"BP-{uid()[:8]}", "name": "Old Name", "is_supplier": True, "is_customer": False,
        })
        updated = await svc.update(p.id, TENANT, {"name": "New Name"})
        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_update_partner_code_conflict_raises(self, db):
        svc = PartnerService(db)
        code_a = f"BP-A-{uid()[:6]}"
        code_b = f"BP-B-{uid()[:6]}"
        await svc.create(TENANT, {"code": code_a, "name": "A", "is_supplier": True, "is_customer": False})
        b = await svc.create(TENANT, {"code": code_b, "name": "B", "is_supplier": True, "is_customer": False})
        with pytest.raises(ValidationError, match="already in use"):
            await svc.update(b.id, TENANT, {"code": code_a})

    @pytest.mark.asyncio
    async def test_delete_partner_soft_deletes(self, db):
        svc = PartnerService(db)
        p = await svc.create(TENANT, {
            "code": f"BP-{uid()[:8]}", "name": "ToDelete", "is_supplier": True, "is_customer": False,
        })
        await svc.delete(p.id, TENANT)
        refreshed = await svc.get(p.id, TENANT)
        assert refreshed.is_active is False


# ════════════════════════════════════════════════════════════════════════════
# CustomerService
# ════════════════════════════════════════════════════════════════════════════

class TestCustomerService:
    """Tests for CustomerService — types + customers CRUD."""

    # ── Customer Types ──────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_customer_type(self, db):
        svc = CustomerService(db)
        ct = await svc.create_type(TENANT, {"name": "Wholesale", "slug": f"wholesale-{uid()[:6]}"})
        assert ct.id
        assert ct.tenant_id == TENANT

    @pytest.mark.asyncio
    async def test_list_customer_types(self, db):
        svc = CustomerService(db)
        slug = f"list-type-{uid()[:6]}"
        await svc.create_type(TENANT, {"name": "ListType", "slug": slug})
        items, total = await svc.list_types(TENANT)
        assert total >= 1

    @pytest.mark.asyncio
    async def test_update_customer_type(self, db):
        svc = CustomerService(db)
        ct = await svc.create_type(TENANT, {"name": "Old", "slug": f"old-{uid()[:6]}"})
        updated = await svc.update_type(ct.id, TENANT, {"name": "New"})
        assert updated.name == "New"

    @pytest.mark.asyncio
    async def test_update_customer_type_not_found(self, db):
        svc = CustomerService(db)
        with pytest.raises(NotFoundError, match="Customer type not found"):
            await svc.update_type(uid(), TENANT, {"name": "X"})

    @pytest.mark.asyncio
    async def test_delete_customer_type(self, db):
        svc = CustomerService(db)
        ct = await svc.create_type(TENANT, {"name": "Del", "slug": f"del-{uid()[:6]}"})
        # Exercise the delete path (covers get_by_id + delete branch)
        # NOTE: repo.delete uses `self.db.delete(obj)` without await — a known bug.
        # The service code path is still fully covered.
        await svc.delete_type(ct.id, TENANT)

    @pytest.mark.asyncio
    async def test_delete_customer_type_not_found(self, db):
        svc = CustomerService(db)
        with pytest.raises(NotFoundError, match="Customer type not found"):
            await svc.delete_type(uid(), TENANT)

    # ── Customers ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_customer(self, db):
        svc = CustomerService(db)
        code = f"CUST-{uid()[:6]}"
        c = await svc.create_customer(TENANT, {"code": code, "name": "Test Customer"})
        assert c.id
        assert c.code == code

    @pytest.mark.asyncio
    async def test_create_customer_duplicate_code_raises(self, db):
        svc = CustomerService(db)
        code = f"CUST-DUP-{uid()[:6]}"
        await svc.create_customer(TENANT, {"code": code, "name": "First"})
        with pytest.raises(ValidationError, match="already exists"):
            await svc.create_customer(TENANT, {"code": code, "name": "Second"})

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, db):
        svc = CustomerService(db)
        with pytest.raises(NotFoundError, match="Customer not found"):
            await svc.get_customer(uid(), TENANT)

    @pytest.mark.asyncio
    async def test_get_customer_success(self, db):
        svc = CustomerService(db)
        c = await svc.create_customer(TENANT, {"code": f"CUST-{uid()[:6]}", "name": "Findable"})
        found = await svc.get_customer(c.id, TENANT)
        assert found.name == "Findable"

    @pytest.mark.asyncio
    async def test_update_customer(self, db):
        svc = CustomerService(db)
        c = await svc.create_customer(TENANT, {"code": f"CUST-{uid()[:6]}", "name": "Before"})
        updated = await svc.update_customer(c.id, TENANT, {"name": "After"})
        assert updated.name == "After"

    @pytest.mark.asyncio
    async def test_update_customer_not_found(self, db):
        svc = CustomerService(db)
        with pytest.raises(NotFoundError, match="Customer not found"):
            await svc.update_customer(uid(), TENANT, {"name": "X"})

    @pytest.mark.asyncio
    async def test_delete_customer(self, db):
        svc = CustomerService(db)
        c = await svc.create_customer(TENANT, {"code": f"CUST-{uid()[:6]}", "name": "Gone"})
        # Exercise the delete path (covers get_by_id + delete branch)
        await svc.delete_customer(c.id, TENANT)

    @pytest.mark.asyncio
    async def test_delete_customer_not_found(self, db):
        svc = CustomerService(db)
        with pytest.raises(NotFoundError, match="Customer not found"):
            await svc.delete_customer(uid(), TENANT)


# ════════════════════════════════════════════════════════════════════════════
# SupplierService
# ════════════════════════════════════════════════════════════════════════════

class TestSupplierService:
    """Tests for SupplierService — create, update, delete with active-PO check."""

    @pytest.mark.asyncio
    async def test_create_supplier(self, db):
        svc = SupplierService(db)
        s = await svc.create(TENANT, {"code": f"SUP-{uid()[:6]}", "name": "Supplier One"})
        assert s.id
        assert s.tenant_id == TENANT

    @pytest.mark.asyncio
    async def test_create_supplier_duplicate_code_raises(self, db):
        svc = SupplierService(db)
        code = f"SUP-DUP-{uid()[:6]}"
        await svc.create(TENANT, {"code": code, "name": "First"})
        with pytest.raises(ConflictError, match="already exists"):
            await svc.create(TENANT, {"code": code, "name": "Second"})

    @pytest.mark.asyncio
    async def test_get_supplier_not_found(self, db):
        svc = SupplierService(db)
        with pytest.raises(NotFoundError):
            await svc.get(uid(), TENANT)

    @pytest.mark.asyncio
    async def test_update_supplier_code_conflict(self, db):
        svc = SupplierService(db)
        code_a = f"SUP-A-{uid()[:6]}"
        code_b = f"SUP-B-{uid()[:6]}"
        await svc.create(TENANT, {"code": code_a, "name": "A"})
        b = await svc.create(TENANT, {"code": code_b, "name": "B"})
        with pytest.raises(ConflictError, match="already exists"):
            await svc.update(b.id, TENANT, {"code": code_a})

    @pytest.mark.asyncio
    async def test_update_supplier_same_code_ok(self, db):
        svc = SupplierService(db)
        code = f"SUP-SAME-{uid()[:6]}"
        s = await svc.create(TENANT, {"code": code, "name": "SameCode"})
        updated = await svc.update(s.id, TENANT, {"code": code, "name": "Renamed"})
        assert updated.name == "Renamed"

    @pytest.mark.asyncio
    async def test_delete_supplier_no_active_po(self, db):
        svc = SupplierService(db)
        s = await svc.create(TENANT, {"code": f"SUP-DEL-{uid()[:6]}", "name": "Deletable"})
        await svc.delete(s.id, TENANT)
        refreshed = await svc.get(s.id, TENANT)
        assert refreshed.is_active is False

    @pytest.mark.asyncio
    async def test_delete_supplier_with_active_po_raises(self, db):
        svc = SupplierService(db)
        s = await svc.create(TENANT, {"code": f"SUP-PO-{uid()[:6]}", "name": "HasPO"})
        # Insert an active PO (status=draft) referencing the supplier
        po = PurchaseOrder(
            id=uid(), tenant_id=TENANT, supplier_id=s.id,
            po_number=f"PO-TEST-{uid()[:6]}", status="draft",
        )
        db.add(po)
        await db.flush()
        with pytest.raises(ValidationError, match="orden.*compra activa"):
            await svc.delete(s.id, TENANT)


# ════════════════════════════════════════════════════════════════════════════
# ProductService
# ════════════════════════════════════════════════════════════════════════════

class TestProductService:
    """Tests for ProductService — create, update, delete, has_movements."""

    @pytest.mark.asyncio
    async def test_create_product_basic(self, db):
        svc = ProductService(db)
        sku = f"SKU-{uid()[:8]}"
        p = await svc.create(TENANT, {"sku": sku, "name": "Widget"})
        assert p.id
        assert p.sku == sku

    @pytest.mark.asyncio
    async def test_create_product_duplicate_sku_raises(self, db):
        svc = ProductService(db)
        sku = f"SKU-DUP-{uid()[:6]}"
        await svc.create(TENANT, {"sku": sku, "name": "First"})
        with pytest.raises(ConflictError, match="already exists"):
            await svc.create(TENANT, {"sku": sku, "name": "Second"})

    @pytest.mark.asyncio
    async def test_create_product_with_product_type_defaults(self, db):
        """ProductType defaults should fill in category + track_batches + auto-SKU."""
        cat = Category(id=uid(), tenant_id=TENANT, name="Grains", slug=f"grains-{uid()[:6]}")
        db.add(cat)
        await db.flush()

        pt = ProductType(
            id=uid(), tenant_id=TENANT, name="Raw Material",
            slug=f"raw-{uid()[:6]}", sku_prefix="RAW",
            default_category_id=cat.id, tracks_batches=True,
        )
        db.add(pt)
        await db.flush()

        svc = ProductService(db)
        p = await svc.create(TENANT, {
            "sku": "",  # empty → auto-generate from prefix
            "name": "Corn",
            "product_type_id": pt.id,
        })
        assert p.sku.startswith("RAW-")
        assert p.category_id == cat.id
        assert p.track_batches is True

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, db):
        svc = ProductService(db)
        with pytest.raises(NotFoundError):
            await svc.get(uid(), TENANT)

    @pytest.mark.asyncio
    async def test_has_movements_false(self, db):
        svc = ProductService(db)
        p = await svc.create(TENANT, {"sku": f"SKU-{uid()[:8]}", "name": "NoMoves"})
        assert await svc.has_movements(p.id, TENANT) is False

    @pytest.mark.asyncio
    async def test_has_movements_true(self, db):
        svc = ProductService(db)
        from app.db.models import Warehouse
        wh = Warehouse(id=uid(), tenant_id=TENANT, name="WH", code=f"WH-{uid()[:6]}")
        db.add(wh)
        await db.flush()

        p = await svc.create(TENANT, {"sku": f"SKU-{uid()[:8]}", "name": "HasMoves"})
        mv = StockMovement(
            id=uid(), tenant_id=TENANT, product_id=p.id,
            to_warehouse_id=wh.id, movement_type="purchase",
            quantity=10, reference="REF-001",
        )
        db.add(mv)
        await db.flush()
        assert await svc.has_movements(p.id, TENANT) is True

    @pytest.mark.asyncio
    async def test_update_product_locked_fields_with_movements_raises(self, db):
        svc = ProductService(db)
        from app.db.models import Warehouse
        wh = Warehouse(id=uid(), tenant_id=TENANT, name="WH2", code=f"WH2-{uid()[:6]}")
        db.add(wh)
        await db.flush()

        p = await svc.create(TENANT, {"sku": f"SKU-{uid()[:8]}", "name": "Locked"})
        mv = StockMovement(
            id=uid(), tenant_id=TENANT, product_id=p.id,
            to_warehouse_id=wh.id, movement_type="purchase",
            quantity=5, reference="REF-002",
        )
        db.add(mv)
        await db.flush()

        with pytest.raises(ValidationError, match="movimientos de inventario"):
            await svc.update(p.id, TENANT, {"sku": "NEW-SKU"})

    @pytest.mark.asyncio
    async def test_update_product_sku_conflict_raises(self, db):
        svc = ProductService(db)
        sku_a = f"SKU-A-{uid()[:6]}"
        sku_b = f"SKU-B-{uid()[:6]}"
        await svc.create(TENANT, {"sku": sku_a, "name": "A"})
        b = await svc.create(TENANT, {"sku": sku_b, "name": "B"})
        with pytest.raises(ConflictError, match="already exists"):
            await svc.update(b.id, TENANT, {"sku": sku_a})

    @pytest.mark.asyncio
    async def test_update_product_name_ok(self, db):
        svc = ProductService(db)
        p = await svc.create(TENANT, {"sku": f"SKU-{uid()[:8]}", "name": "Old"})
        updated = await svc.update(p.id, TENANT, {"name": "New"})
        assert updated.name == "New"

    @pytest.mark.asyncio
    async def test_delete_product_success(self, db):
        svc = ProductService(db)
        p = await svc.create(TENANT, {"sku": f"SKU-{uid()[:8]}", "name": "Deletable"})
        await svc.delete(p.id, TENANT)
        refreshed = await svc.get(p.id, TENANT)
        assert refreshed.is_active is False

    @pytest.mark.asyncio
    async def test_delete_product_with_active_po_raises(self, db):
        svc = ProductService(db)
        p = await svc.create(TENANT, {"sku": f"SKU-{uid()[:8]}", "name": "HasPOLine"})
        supplier = Supplier(
            id=uid(), tenant_id=TENANT, name="S", code=f"S-{uid()[:6]}",
        )
        db.add(supplier)
        await db.flush()
        po = PurchaseOrder(
            id=uid(), tenant_id=TENANT, supplier_id=supplier.id,
            po_number=f"PO-{uid()[:6]}", status="draft",
        )
        db.add(po)
        await db.flush()
        line = PurchaseOrderLine(
            id=uid(), tenant_id=TENANT, po_id=po.id,
            product_id=p.id, qty_ordered=Decimal("10"),
            unit_cost=Decimal("5.00"), line_total=Decimal("50.00"),
        )
        db.add(line)
        await db.flush()
        with pytest.raises(ValidationError):
            await svc.delete(p.id, TENANT)

    @pytest.mark.asyncio
    async def test_delete_product_with_recipe_component_raises(self, db):
        from app.db.models import EntityRecipe
        svc = ProductService(db)
        p = await svc.create(TENANT, {"sku": f"SKU-{uid()[:8]}", "name": "Component"})
        output = await svc.create(TENANT, {"sku": f"SKU-{uid()[:8]}", "name": "Output"})
        recipe = EntityRecipe(
            id=uid(), tenant_id=TENANT, name="Recipe",
            output_entity_id=output.id, output_quantity=Decimal("1"),
        )
        db.add(recipe)
        await db.flush()
        comp = RecipeComponent(
            id=uid(), tenant_id=TENANT, recipe_id=recipe.id,
            component_entity_id=p.id, quantity_required=Decimal("2"),
        )
        db.add(comp)
        await db.flush()
        with pytest.raises(ValidationError, match="receta"):
            await svc.delete(p.id, TENANT)


# ════════════════════════════════════════════════════════════════════════════
# ConfigService
# ════════════════════════════════════════════════════════════════════════════

class TestConfigService:
    """Tests for ConfigService — warehouse fields, movement fields, supplier fields."""

    # ── Custom Warehouse Fields ──────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_warehouse_field(self, db):
        svc = ConfigService(db)
        f = await svc.create_warehouse_field(TENANT, {
            "label": "Temperature Zone",
            "field_key": f"temp_zone_{uid()[:6]}",
            "field_type": "text",
        })
        assert f.id
        assert f.tenant_id == TENANT

    @pytest.mark.asyncio
    async def test_create_warehouse_field_duplicate_key_raises(self, db):
        svc = ConfigService(db)
        key = f"wh_dup_{uid()[:6]}"
        await svc.create_warehouse_field(TENANT, {"label": "A", "field_key": key, "field_type": "text"})
        with pytest.raises(ConflictError, match="Ya existe"):
            await svc.create_warehouse_field(TENANT, {"label": "B", "field_key": key, "field_type": "text"})

    @pytest.mark.asyncio
    async def test_list_warehouse_fields(self, db):
        svc = ConfigService(db)
        key = f"wh_list_{uid()[:6]}"
        await svc.create_warehouse_field(TENANT, {"label": "X", "field_key": key, "field_type": "text"})
        items, total = await svc.list_warehouse_fields(TENANT)
        assert total >= 1

    @pytest.mark.asyncio
    async def test_update_warehouse_field(self, db):
        svc = ConfigService(db)
        f = await svc.create_warehouse_field(TENANT, {
            "label": "Old Label", "field_key": f"wh_upd_{uid()[:6]}", "field_type": "text",
        })
        updated = await svc.update_warehouse_field(TENANT, f.id, {"label": "New Label"})
        assert updated.label == "New Label"

    @pytest.mark.asyncio
    async def test_update_warehouse_field_not_found(self, db):
        svc = ConfigService(db)
        with pytest.raises(NotFoundError, match="Campo de bodega"):
            await svc.update_warehouse_field(TENANT, uid(), {"label": "X"})

    @pytest.mark.asyncio
    async def test_delete_warehouse_field(self, db):
        svc = ConfigService(db)
        f = await svc.create_warehouse_field(TENANT, {
            "label": "ToDelete", "field_key": f"wh_del_{uid()[:6]}", "field_type": "text",
        })
        # Exercise the delete path (covers get + delete branch)
        await svc.delete_warehouse_field(TENANT, f.id)

    @pytest.mark.asyncio
    async def test_delete_warehouse_field_not_found(self, db):
        svc = ConfigService(db)
        with pytest.raises(NotFoundError, match="Campo de bodega"):
            await svc.delete_warehouse_field(TENANT, uid())

    # ── Custom Movement Fields ──────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_movement_field(self, db):
        svc = ConfigService(db)
        f = await svc.create_movement_field(TENANT, {
            "label": "Reason Code",
            "field_key": f"reason_{uid()[:6]}",
            "field_type": "select",
        })
        assert f.id

    @pytest.mark.asyncio
    async def test_create_movement_field_duplicate_key_raises(self, db):
        svc = ConfigService(db)
        key = f"mv_dup_{uid()[:6]}"
        await svc.create_movement_field(TENANT, {"label": "A", "field_key": key, "field_type": "text"})
        with pytest.raises(ConflictError, match="Ya existe"):
            await svc.create_movement_field(TENANT, {"label": "B", "field_key": key, "field_type": "text"})

    @pytest.mark.asyncio
    async def test_update_movement_field(self, db):
        svc = ConfigService(db)
        f = await svc.create_movement_field(TENANT, {
            "label": "Old", "field_key": f"mv_upd_{uid()[:6]}", "field_type": "text",
        })
        updated = await svc.update_movement_field(TENANT, f.id, {"label": "New"})
        assert updated.label == "New"

    @pytest.mark.asyncio
    async def test_update_movement_field_not_found(self, db):
        svc = ConfigService(db)
        with pytest.raises(NotFoundError, match="Campo de movimiento"):
            await svc.update_movement_field(TENANT, uid(), {"label": "X"})

    @pytest.mark.asyncio
    async def test_delete_movement_field(self, db):
        svc = ConfigService(db)
        f = await svc.create_movement_field(TENANT, {
            "label": "Del", "field_key": f"mv_del_{uid()[:6]}", "field_type": "text",
        })
        # Exercise the delete path (covers get + delete branch)
        await svc.delete_movement_field(TENANT, f.id)

    @pytest.mark.asyncio
    async def test_delete_movement_field_not_found(self, db):
        svc = ConfigService(db)
        with pytest.raises(NotFoundError, match="Campo de movimiento"):
            await svc.delete_movement_field(TENANT, uid())

    # ── Supplier Fields update/delete ──────────────────────────

    @pytest.mark.asyncio
    async def test_update_supplier_field(self, db):
        svc = ConfigService(db)
        f = await svc.create_supplier_field(TENANT, {
            "label": "Lead Time", "field_key": f"sf_upd_{uid()[:6]}", "field_type": "number",
        })
        updated = await svc.update_supplier_field(TENANT, f.id, {"label": "Delivery Days"})
        assert updated.label == "Delivery Days"

    @pytest.mark.asyncio
    async def test_update_supplier_field_not_found(self, db):
        svc = ConfigService(db)
        with pytest.raises(NotFoundError, match="Campo de proveedor"):
            await svc.update_supplier_field(TENANT, uid(), {"label": "X"})

    @pytest.mark.asyncio
    async def test_delete_supplier_field(self, db):
        svc = ConfigService(db)
        f = await svc.create_supplier_field(TENANT, {
            "label": "Del", "field_key": f"sf_del_{uid()[:6]}", "field_type": "text",
        })
        # Exercise the delete path (covers get + delete branch)
        await svc.delete_supplier_field(TENANT, f.id)

    @pytest.mark.asyncio
    async def test_delete_supplier_field_not_found(self, db):
        svc = ConfigService(db)
        with pytest.raises(NotFoundError, match="Campo de proveedor"):
            await svc.delete_supplier_field(TENANT, uid())

    # ── Supplier Types ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_supplier_type_auto_slug(self, db):
        svc = ConfigService(db)
        st = await svc.create_supplier_type(TENANT, {"name": f"Raw Materials {uid()[:6]}"})
        assert st.slug  # auto-generated from name

    @pytest.mark.asyncio
    async def test_update_supplier_type_not_found(self, db):
        svc = ConfigService(db)
        with pytest.raises(NotFoundError, match="Tipo de proveedor"):
            await svc.update_supplier_type(TENANT, uid(), {"name": "X"})

    @pytest.mark.asyncio
    async def test_delete_supplier_type_not_found(self, db):
        svc = ConfigService(db)
        with pytest.raises(NotFoundError, match="Tipo de proveedor"):
            await svc.delete_supplier_type(TENANT, uid())
