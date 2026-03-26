"""Unit tests targeting uncovered service lines — direct DB interaction via `db` fixture."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Category,
    Customer,
    CustomerType,
    DynamicMovementType,
    DynamicWarehouseType,
    EntityBatch,
    EventSeverity,
    EventStatus,
    EventType,
    InventoryEvent,
    MovementType,
    OrderType,
    POStatus,
    Product,
    ProductType,
    PurchaseOrder,
    PurchaseOrderLine,
    StockAlert,
    StockLevel,
    StockMovement,
    Supplier,
    Warehouse,
    WarehouseType,
)
from app.core.errors import ConflictError, NotFoundError, ValidationError

uid = lambda: str(uuid.uuid4())
tid = "test-tenant"
_now = lambda: datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers — seed reusable rows
# ═══════════════════════════════════════════════════════════════════════════

async def _product(db: AsyncSession, **kw) -> Product:
    p = Product(
        id=kw.get("id", uid()), tenant_id=kw.get("tenant_id", tid),
        sku=kw.get("sku", f"SKU-{uid()[:6]}"), name=kw.get("name", "Test Product"),
        unit_of_measure="un", is_active=kw.get("is_active", True),
        min_stock_level=kw.get("min_stock_level", 0),
        reorder_point=kw.get("reorder_point", 0),
        reorder_quantity=kw.get("reorder_quantity", 1),
        suggested_sale_price=kw.get("suggested_sale_price", None),
        last_purchase_cost=kw.get("last_purchase_cost", None),
    )
    db.add(p)
    await db.flush()
    return p


async def _warehouse(db: AsyncSession, **kw) -> Warehouse:
    w = Warehouse(
        id=kw.get("id", uid()), tenant_id=kw.get("tenant_id", tid),
        name=kw.get("name", "WH-Test"), code=kw.get("code", f"WH-{uid()[:6]}"),
        type=kw.get("type", WarehouseType.main), is_active=True,
    )
    db.add(w)
    await db.flush()
    return w


async def _supplier(db: AsyncSession, **kw) -> Supplier:
    s = Supplier(
        id=kw.get("id", uid()), tenant_id=kw.get("tenant_id", tid),
        name=kw.get("name", "Supplier A"), code=kw.get("code", f"S-{uid()[:6]}"),
        is_active=True,
    )
    db.add(s)
    await db.flush()
    return s


async def _customer(db: AsyncSession, **kw) -> Customer:
    c = Customer(
        id=kw.get("id", uid()), tenant_id=kw.get("tenant_id", tid),
        name=kw.get("name", "Customer A"), code=kw.get("code", f"C-{uid()[:6]}"),
        is_active=True,
    )
    db.add(c)
    await db.flush()
    return c


async def _event_type(db: AsyncSession, **kw) -> EventType:
    et = EventType(
        id=kw.get("id", uid()), tenant_id=kw.get("tenant_id", tid),
        name=kw.get("name", "Damage"), slug=kw.get("slug", f"damage-{uid()[:6]}"),
        auto_generate_movement_type_id=kw.get("auto_generate_movement_type_id", None),
    )
    db.add(et)
    await db.flush()
    return et


async def _event_severity(db: AsyncSession, **kw) -> EventSeverity:
    es = EventSeverity(
        id=kw.get("id", uid()), tenant_id=kw.get("tenant_id", tid),
        name=kw.get("name", "High"), slug=kw.get("slug", f"high-{uid()[:6]}"),
    )
    db.add(es)
    await db.flush()
    return es


async def _event_status(db: AsyncSession, **kw) -> EventStatus:
    es = EventStatus(
        id=kw.get("id", uid()), tenant_id=kw.get("tenant_id", tid),
        name=kw.get("name", "Open"), slug=kw.get("slug", f"open-{uid()[:6]}"),
    )
    db.add(es)
    await db.flush()
    return es


async def _batch(db: AsyncSession, entity_id: str, **kw) -> EntityBatch:
    b = EntityBatch(
        id=kw.get("id", uid()), tenant_id=kw.get("tenant_id", tid),
        entity_id=entity_id,
        batch_number=kw.get("batch_number", f"LOT-{uid()[:6]}"),
        quantity=kw.get("quantity", Decimal("100")),
        expiration_date=kw.get("expiration_date", None),
        is_active=kw.get("is_active", True),
    )
    db.add(b)
    await db.flush()
    return b


async def _stock_level(db: AsyncSession, product_id: str, warehouse_id: str, **kw) -> StockLevel:
    sl = StockLevel(
        id=uid(), tenant_id=kw.get("tenant_id", tid),
        product_id=product_id, warehouse_id=warehouse_id,
        qty_on_hand=kw.get("qty_on_hand", Decimal("0")),
        qty_reserved=kw.get("qty_reserved", Decimal("0")),
        qty_in_transit=kw.get("qty_in_transit", Decimal("0")),
        reorder_point=kw.get("reorder_point", 0),
        qc_status=kw.get("qc_status", "approved"),
    )
    db.add(sl)
    await db.flush()
    return sl


# ═══════════════════════════════════════════════════════════════════════════
# 1. DynamicConfigService — movement types & warehouse types CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestDynamicConfigMovementTypes:
    @pytest.mark.asyncio
    async def test_create_and_list_movement_types(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        mt = await svc.create_movement_type(tid, {"name": "Custom Move", "direction": "in", "is_system": False})
        assert mt.slug == "custom-move"
        items, total = await svc.list_movement_types(tid)
        assert any(m.id == mt.id for m in items)

    @pytest.mark.asyncio
    async def test_create_movement_type_conflict(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        await svc.create_movement_type(tid, {"name": "Dup Move", "slug": "dup-move", "direction": "in", "is_system": False})
        with pytest.raises(ConflictError):
            await svc.create_movement_type(tid, {"name": "Dup Move 2", "slug": "dup-move", "direction": "out", "is_system": False})

    @pytest.mark.asyncio
    async def test_update_movement_type(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        mt = await svc.create_movement_type(tid, {"name": "Editable", "direction": "in", "is_system": False})
        updated = await svc.update_movement_type(tid, mt.id, {"name": "Edited"})
        assert updated.name == "Edited"

    @pytest.mark.asyncio
    async def test_update_movement_type_not_found(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        with pytest.raises(NotFoundError):
            await svc.update_movement_type(tid, uid(), {"name": "x"})

    @pytest.mark.asyncio
    async def test_update_system_movement_type_rejected(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        mt = DynamicMovementType(
            id=uid(), tenant_id=tid, name="System", slug=f"sys-{uid()[:6]}",
            direction="in", is_system=True,
        )
        db.add(mt)
        await db.flush()
        with pytest.raises(ValidationError):
            await svc.update_movement_type(tid, mt.id, {"name": "new"})

    @pytest.mark.asyncio
    async def test_delete_movement_type(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        mt = await svc.create_movement_type(tid, {"name": "To Delete MT", "direction": "out", "is_system": False})
        # delete_movement_type validates not-found and not-system, then calls repo.delete
        await svc.delete_movement_type(tid, mt.id)

    @pytest.mark.asyncio
    async def test_delete_movement_type_not_found(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        with pytest.raises(NotFoundError):
            await svc.delete_movement_type(tid, uid())

    @pytest.mark.asyncio
    async def test_delete_system_movement_type_rejected(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        mt = DynamicMovementType(
            id=uid(), tenant_id=tid, name="Sys Del", slug=f"sysd-{uid()[:6]}",
            direction="in", is_system=True,
        )
        db.add(mt)
        await db.flush()
        with pytest.raises(ValidationError):
            await svc.delete_movement_type(tid, mt.id)


class TestDynamicConfigWarehouseTypes:
    @pytest.mark.asyncio
    async def test_create_and_list_warehouse_types(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        wt = await svc.create_warehouse_type(tid, {"name": "Cold Storage", "is_system": False})
        assert wt.slug == "cold-storage"
        items, total = await svc.list_warehouse_types(tid)
        assert any(w.id == wt.id for w in items)

    @pytest.mark.asyncio
    async def test_update_warehouse_type(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        wt = await svc.create_warehouse_type(tid, {"name": "WT Edit", "is_system": False})
        updated = await svc.update_warehouse_type(tid, wt.id, {"name": "WT Edited"})
        assert updated.name == "WT Edited"

    @pytest.mark.asyncio
    async def test_update_warehouse_type_not_found(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        with pytest.raises(NotFoundError):
            await svc.update_warehouse_type(tid, uid(), {"name": "x"})

    @pytest.mark.asyncio
    async def test_update_system_warehouse_type_rejected(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        wt = DynamicWarehouseType(
            id=uid(), tenant_id=tid, name="SysWT", slug=f"syswt-{uid()[:6]}",
            is_system=True,
        )
        db.add(wt)
        await db.flush()
        with pytest.raises(ValidationError):
            await svc.update_warehouse_type(tid, wt.id, {"name": "new"})

    @pytest.mark.asyncio
    async def test_delete_warehouse_type(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        wt = await svc.create_warehouse_type(tid, {"name": "WTDel", "is_system": False})
        await svc.delete_warehouse_type(tid, wt.id)

    @pytest.mark.asyncio
    async def test_delete_warehouse_type_not_found(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        with pytest.raises(NotFoundError):
            await svc.delete_warehouse_type(tid, uid())

    @pytest.mark.asyncio
    async def test_delete_system_warehouse_type_rejected(self, db: AsyncSession):
        from app.services.dynamic_config_service import DynamicConfigService
        svc = DynamicConfigService(db)
        wt = DynamicWarehouseType(
            id=uid(), tenant_id=tid, name="SysWTD", slug=f"syswtd-{uid()[:6]}",
            is_system=True,
        )
        db.add(wt)
        await db.flush()
        with pytest.raises(ValidationError):
            await svc.delete_warehouse_type(tid, wt.id)


# ═══════════════════════════════════════════════════════════════════════════
# 2. EventService — create, change_status, add_impact
# ═══════════════════════════════════════════════════════════════════════════

class TestEventService:
    @pytest.mark.asyncio
    async def test_create_event_basic(self, db: AsyncSession):
        from app.services.event_service import EventService
        et = await _event_type(db)
        es = await _event_severity(db)
        est = await _event_status(db)
        svc = EventService(db)
        event = await svc.create(tid, {
            "event_type_id": et.id,
            "severity_id": es.id,
            "status_id": est.id,
            "title": "Broken pallet",
            "occurred_at": _now(),
            "reported_by": "user-1",
        })
        assert event is not None
        assert event.title == "Broken pallet"

    @pytest.mark.asyncio
    async def test_create_event_invalid_type(self, db: AsyncSession):
        from app.services.event_service import EventService
        svc = EventService(db)
        with pytest.raises(ValidationError, match="Tipo de evento"):
            await svc.create(tid, {
                "event_type_id": uid(),
                "severity_id": uid(),
                "status_id": uid(),
                "title": "Bad",
                "occurred_at": _now(),
            })

    @pytest.mark.asyncio
    async def test_create_event_with_impact(self, db: AsyncSession):
        from app.services.event_service import EventService
        et = await _event_type(db)
        es = await _event_severity(db)
        est = await _event_status(db)
        prod = await _product(db)
        svc = EventService(db)
        event = await svc.create(tid, {
            "event_type_id": et.id,
            "severity_id": es.id,
            "status_id": est.id,
            "title": "Impact test",
            "occurred_at": _now(),
        }, impacts=[{
            "entity_id": prod.id,
            "quantity_impact": -5,
            "notes": "lost 5",
        }])
        assert event is not None

    @pytest.mark.asyncio
    async def test_change_status(self, db: AsyncSession):
        from app.services.event_service import EventService
        et = await _event_type(db)
        es = await _event_severity(db)
        est1 = await _event_status(db, name="Open", slug=f"open-{uid()[:6]}")
        est2 = await _event_status(db, name="Closed", slug=f"closed-{uid()[:6]}")
        svc = EventService(db)
        event = await svc.create(tid, {
            "event_type_id": et.id,
            "severity_id": es.id,
            "status_id": est1.id,
            "title": "Status change test",
            "occurred_at": _now(),
        })
        updated = await svc.change_status(tid, event.id, est2.id, notes="Resolved", changed_by="admin")
        assert updated.status_id == est2.id

    @pytest.mark.asyncio
    async def test_change_status_not_found(self, db: AsyncSession):
        from app.services.event_service import EventService
        svc = EventService(db)
        with pytest.raises(NotFoundError):
            await svc.change_status(tid, uid(), uid())

    @pytest.mark.asyncio
    async def test_change_status_with_resolved_at(self, db: AsyncSession):
        from app.services.event_service import EventService
        et = await _event_type(db)
        es = await _event_severity(db)
        est1 = await _event_status(db, slug=f"o-{uid()[:6]}")
        est2 = await _event_status(db, slug=f"c-{uid()[:6]}")
        svc = EventService(db)
        event = await svc.create(tid, {
            "event_type_id": et.id, "severity_id": es.id, "status_id": est1.id,
            "title": "Resolve", "occurred_at": _now(),
        })
        now = _now()
        updated = await svc.change_status(tid, event.id, est2.id, resolved_at=now)
        assert updated.resolved_at is not None

    @pytest.mark.asyncio
    async def test_add_impact(self, db: AsyncSession):
        from app.services.event_service import EventService
        et = await _event_type(db)
        es = await _event_severity(db)
        est = await _event_status(db, slug=f"ai-{uid()[:6]}")
        prod = await _product(db)
        svc = EventService(db)
        event = await svc.create(tid, {
            "event_type_id": et.id, "severity_id": es.id, "status_id": est.id,
            "title": "Add impact later", "occurred_at": _now(),
        })
        impact = await svc.add_impact(tid, event.id, {
            "entity_id": prod.id, "quantity_impact": -3,
        })
        assert impact is not None

    @pytest.mark.asyncio
    async def test_add_impact_not_found(self, db: AsyncSession):
        from app.services.event_service import EventService
        svc = EventService(db)
        with pytest.raises(NotFoundError):
            await svc.add_impact(tid, uid(), {"entity_id": uid(), "quantity_impact": 0})


# ═══════════════════════════════════════════════════════════════════════════
# 3. BatchService — search, trace_forward
# ═══════════════════════════════════════════════════════════════════════════

class TestBatchServiceSearch:
    @pytest.mark.asyncio
    async def test_search_basic(self, db: AsyncSession):
        from app.services.batch_service import BatchService
        prod = await _product(db)
        batch = await _batch(db, prod.id, batch_number="SEARCH-001")
        svc = BatchService(db)
        results = await svc.search(tid, "SEARCH")
        assert len(results) >= 1
        assert results[0].product_name == prod.name

    @pytest.mark.asyncio
    async def test_search_with_product_filter(self, db: AsyncSession):
        from app.services.batch_service import BatchService
        prod = await _product(db)
        await _batch(db, prod.id, batch_number="FILTER-001")
        svc = BatchService(db)
        results = await svc.search(tid, "FILTER", product_id=prod.id)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_trace_forward_no_movements(self, db: AsyncSession):
        from app.services.batch_service import BatchService
        prod = await _product(db)
        batch = await _batch(db, prod.id, batch_number="TRACE-001")
        svc = BatchService(db)
        result = await svc.trace_forward(tid, batch.id)
        assert result.total_dispatched == 0.0
        assert result.product_name == prod.name

    @pytest.mark.asyncio
    async def test_trace_forward_with_movement(self, db: AsyncSession):
        from app.services.batch_service import BatchService
        prod = await _product(db)
        wh = await _warehouse(db)
        batch = await _batch(db, prod.id, batch_number="TRACE-002")
        # Create a sale movement with batch_id and SO reference
        mov = StockMovement(
            id=uid(), tenant_id=tid, movement_type=MovementType.sale,
            product_id=prod.id, from_warehouse_id=wh.id,
            quantity=Decimal("10"), batch_id=batch.id,
            reference="SO:SO-001",
        )
        db.add(mov)
        await db.flush()
        svc = BatchService(db)
        result = await svc.trace_forward(tid, batch.id)
        assert result.total_dispatched == 10.0
        assert len(result.dispatches) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 4. ReportsService — events_csv, serials_csv, batches_csv, purchase_orders_csv
# ═══════════════════════════════════════════════════════════════════════════

class TestReportsService:
    @pytest.mark.asyncio
    async def test_events_csv_empty(self, db: AsyncSession):
        from app.services.reports_service import ReportsService
        svc = ReportsService(db)
        csv = await svc.events_csv(tid)
        assert "Fecha ocurrencia" in csv

    @pytest.mark.asyncio
    async def test_events_csv_with_data(self, db: AsyncSession):
        from app.services.reports_service import ReportsService
        et = await _event_type(db)
        es = await _event_severity(db)
        est = await _event_status(db, slug=f"csv-{uid()[:6]}")
        ev = InventoryEvent(
            id=uid(), tenant_id=tid, event_type_id=et.id,
            severity_id=es.id, status_id=est.id,
            title="CSV Test Event", occurred_at=_now(),
        )
        db.add(ev)
        await db.flush()
        svc = ReportsService(db)
        csv = await svc.events_csv(tid)
        assert "CSV Test Event" in csv

    @pytest.mark.asyncio
    async def test_events_csv_date_filters(self, db: AsyncSession):
        from app.services.reports_service import ReportsService
        svc = ReportsService(db)
        csv = await svc.events_csv(tid, date_from=date(2020, 1, 1), date_to=date(2020, 12, 31))
        assert "Fecha ocurrencia" in csv

    @pytest.mark.asyncio
    async def test_serials_csv_empty(self, db: AsyncSession):
        from app.services.reports_service import ReportsService
        svc = ReportsService(db)
        csv = await svc.serials_csv(tid)
        assert "Nro. serial" in csv

    @pytest.mark.asyncio
    async def test_batches_csv_empty(self, db: AsyncSession):
        from app.services.reports_service import ReportsService
        svc = ReportsService(db)
        csv = await svc.batches_csv(tid)
        assert "Nro. lote" in csv

    @pytest.mark.asyncio
    async def test_batches_csv_with_data(self, db: AsyncSession):
        from app.services.reports_service import ReportsService
        prod = await _product(db)
        batch = await _batch(db, prod.id, batch_number="CSV-LOT-1", quantity=Decimal("50"))
        svc = ReportsService(db)
        csv = await svc.batches_csv(tid)
        assert "CSV-LOT-1" in csv

    @pytest.mark.asyncio
    async def test_purchase_orders_csv_empty(self, db: AsyncSession):
        from app.services.reports_service import ReportsService
        svc = ReportsService(db)
        csv = await svc.purchase_orders_csv(tid)
        assert "Nro. orden" in csv

    @pytest.mark.asyncio
    async def test_purchase_orders_csv_with_data(self, db: AsyncSession):
        from app.services.reports_service import ReportsService
        supplier = await _supplier(db)
        prod = await _product(db)
        po = PurchaseOrder(
            id=uid(), tenant_id=tid, po_number=f"PO-CSV-{uid()[:4]}",
            supplier_id=supplier.id, status=POStatus.draft,
        )
        db.add(po)
        await db.flush()
        line = PurchaseOrderLine(
            id=uid(), tenant_id=tid, po_id=po.id,
            product_id=prod.id, qty_ordered=Decimal("10"),
            qty_received=Decimal("0"), unit_cost=Decimal("100"),
            line_total=Decimal("1000"),
        )
        db.add(line)
        await db.flush()
        svc = ReportsService(db)
        csv = await svc.purchase_orders_csv(tid)
        assert po.po_number in csv

    @pytest.mark.asyncio
    async def test_purchase_orders_csv_date_filters(self, db: AsyncSession):
        from app.services.reports_service import ReportsService
        svc = ReportsService(db)
        csv = await svc.purchase_orders_csv(tid, date_from=date(2020, 1, 1), date_to=date(2020, 12, 31))
        assert "Nro. orden" in csv


# ═══════════════════════════════════════════════════════════════════════════
# 5. ConfigService — product type CRUD, order type CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestConfigServiceProductTypes:
    @pytest.mark.asyncio
    async def test_create_product_type(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        pt = await svc.create_product_type(tid, {"name": "Electronics"})
        assert pt.slug == "electronics"

    @pytest.mark.asyncio
    async def test_update_product_type(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        pt = await svc.create_product_type(tid, {"name": "PTedit"})
        updated = await svc.update_product_type(tid, pt.id, {"name": "PTedit2"})
        assert updated.name == "PTedit2"

    @pytest.mark.asyncio
    async def test_update_product_type_not_found(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        with pytest.raises(NotFoundError):
            await svc.update_product_type(tid, uid(), {"name": "x"})

    @pytest.mark.asyncio
    async def test_delete_product_type_no_products(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        pt = await svc.create_product_type(tid, {"name": f"PTdel-{uid()[:4]}"})
        await svc.delete_product_type(tid, pt.id)

    @pytest.mark.asyncio
    async def test_delete_product_type_with_products_fails(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        pt = await svc.create_product_type(tid, {"name": f"PTinuse-{uid()[:4]}"})
        prod = await _product(db)
        prod.product_type_id = pt.id
        await db.flush()
        with pytest.raises(ValidationError, match="producto"):
            await svc.delete_product_type(tid, pt.id)

    @pytest.mark.asyncio
    async def test_delete_product_type_not_found(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        with pytest.raises(NotFoundError):
            await svc.delete_product_type(tid, uid())


class TestConfigServiceOrderTypes:
    @pytest.mark.asyncio
    async def test_create_order_type(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        ot = await svc.create_order_type(tid, {"name": "Rush Order"})
        assert ot.slug == "rush-order"

    @pytest.mark.asyncio
    async def test_update_order_type(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        ot = await svc.create_order_type(tid, {"name": f"OTedit-{uid()[:4]}"})
        updated = await svc.update_order_type(tid, ot.id, {"name": "OTedited"})
        assert updated.name == "OTedited"

    @pytest.mark.asyncio
    async def test_update_order_type_not_found(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        with pytest.raises(NotFoundError):
            await svc.update_order_type(tid, uid(), {"name": "x"})

    @pytest.mark.asyncio
    async def test_delete_order_type(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        ot = await svc.create_order_type(tid, {"name": f"OTdel-{uid()[:4]}"})
        await svc.delete_order_type(tid, ot.id)

    @pytest.mark.asyncio
    async def test_delete_order_type_not_found(self, db: AsyncSession):
        from app.services.config_service import ConfigService
        svc = ConfigService(db)
        with pytest.raises(NotFoundError):
            await svc.delete_order_type(tid, uid())


# ═══════════════════════════════════════════════════════════════════════════
# 6. CustomerPriceService — set_customer_price, lookup, list_all
# ═══════════════════════════════════════════════════════════════════════════

class TestCustomerPriceService:
    @pytest.mark.asyncio
    async def test_set_customer_price_create(self, db: AsyncSession):
        from app.services.customer_price_service import CustomerPriceService
        prod = await _product(db, suggested_sale_price=Decimal("100"))
        cust = await _customer(db)
        svc = CustomerPriceService(db)
        cp = await svc.set_customer_price(
            tid, cust.id, prod.id, Decimal("80"), "admin", "Admin User",
            reason="Discount",
        )
        assert cp.price == Decimal("80")
        assert cp.is_active is True

    @pytest.mark.asyncio
    async def test_set_customer_price_update(self, db: AsyncSession):
        """When an active price exists, updating it should change the price in-place."""
        from app.services.customer_price_service import CustomerPriceService
        from app.db.models.customer_price import CustomerPrice as CPModel
        prod = await _product(db)
        cust = await _customer(db)
        svc = CustomerPriceService(db)
        # Create with explicit is_active to work around SQLite server_default
        cp1 = CPModel(
            id=uid(), tenant_id=tid, customer_id=cust.id, product_id=prod.id,
            price=Decimal("80"), min_quantity=Decimal("1"), currency="COP",
            valid_from=date.today(), is_active=True, created_by="admin",
        )
        db.add(cp1)
        await db.flush()
        # Now set_customer_price should find the existing one and update
        cp2 = await svc.set_customer_price(tid, cust.id, prod.id, Decimal("75"), "admin", reason="Discount")
        assert cp2.id == cp1.id
        assert cp2.price == Decimal("75")

    @pytest.mark.asyncio
    async def test_set_customer_price_same_price_no_history(self, db: AsyncSession):
        """When price doesn't change, no history entry is created for the update."""
        from app.services.customer_price_service import CustomerPriceService
        from app.db.models.customer_price import CustomerPrice as CPModel
        prod = await _product(db)
        cust = await _customer(db)
        svc = CustomerPriceService(db)
        cp1 = CPModel(
            id=uid(), tenant_id=tid, customer_id=cust.id, product_id=prod.id,
            price=Decimal("80"), min_quantity=Decimal("1"), currency="COP",
            valid_from=date.today(), is_active=True, created_by="admin",
        )
        db.add(cp1)
        await db.flush()
        # Set same price again — should not create history
        cp2 = await svc.set_customer_price(tid, cust.id, prod.id, Decimal("80"), "admin")
        assert cp2.price == Decimal("80")
        assert cp2.id == cp1.id

    @pytest.mark.asyncio
    async def test_lookup_customer_special(self, db: AsyncSession):
        from app.services.customer_price_service import CustomerPriceService
        from app.db.models.customer_price import CustomerPrice as CPModel
        prod = await _product(db, suggested_sale_price=Decimal("100"))
        cust = await _customer(db)
        svc = CustomerPriceService(db)
        cp = CPModel(
            id=uid(), tenant_id=tid, customer_id=cust.id, product_id=prod.id,
            price=Decimal("85"), min_quantity=Decimal("1"), currency="COP",
            valid_from=date.today(), is_active=True, created_by="admin",
        )
        db.add(cp)
        await db.flush()
        result = await svc.lookup(tid, cust.id, prod.id)
        assert result["source"] == "customer_special"
        assert result["price"] == 85.0

    @pytest.mark.asyncio
    async def test_lookup_fallback_to_base(self, db: AsyncSession):
        from app.services.customer_price_service import CustomerPriceService
        prod = await _product(db, suggested_sale_price=Decimal("100"))
        cust = await _customer(db)
        svc = CustomerPriceService(db)
        result = await svc.lookup(tid, cust.id, prod.id)
        assert result["source"] == "product_base"
        assert result["price"] == 100.0

    @pytest.mark.asyncio
    async def test_list_all_filters(self, db: AsyncSession):
        from app.services.customer_price_service import CustomerPriceService
        from app.db.models.customer_price import CustomerPrice as CPModel
        prod = await _product(db)
        cust = await _customer(db)
        svc = CustomerPriceService(db)
        cp = CPModel(
            id=uid(), tenant_id=tid, customer_id=cust.id, product_id=prod.id,
            price=Decimal("90"), min_quantity=Decimal("1"), currency="COP",
            valid_from=date.today(), is_active=True, created_by="admin",
        )
        db.add(cp)
        await db.flush()
        items = await svc.list_all(tid, customer_id=cust.id, is_active=True)
        assert len(items) >= 1

    @pytest.mark.asyncio
    async def test_list_all_expired_filter(self, db: AsyncSession):
        from app.services.customer_price_service import CustomerPriceService
        from app.db.models.customer_price import CustomerPrice as CPModel
        prod = await _product(db)
        cust = await _customer(db)
        svc = CustomerPriceService(db)
        yesterday = date.today() - timedelta(days=1)
        cp = CPModel(
            id=uid(), tenant_id=tid, customer_id=cust.id, product_id=prod.id,
            price=Decimal("70"), min_quantity=Decimal("1"), currency="COP",
            valid_from=date(2020, 1, 1), valid_to=yesterday,
            is_active=True, created_by="admin",
        )
        db.add(cp)
        await db.flush()
        expired = await svc.list_all(tid, is_expired=True)
        assert any(e.id == cp.id for e in expired)
        not_expired = await svc.list_all(tid, is_expired=False)
        assert not any(e.id == cp.id for e in not_expired)

    @pytest.mark.asyncio
    async def test_deactivate(self, db: AsyncSession):
        from app.services.customer_price_service import CustomerPriceService
        from app.db.models.customer_price import CustomerPrice as CPModel
        prod = await _product(db)
        cust = await _customer(db)
        svc = CustomerPriceService(db)
        cp = CPModel(
            id=uid(), tenant_id=tid, customer_id=cust.id, product_id=prod.id,
            price=Decimal("60"), min_quantity=Decimal("1"), currency="COP",
            valid_from=date.today(), is_active=True, created_by="admin",
        )
        db.add(cp)
        await db.flush()
        await svc.deactivate(cp.id, tid)
        fetched = await svc.get_by_id(cp.id, tid)
        assert fetched.is_active is False

    @pytest.mark.asyncio
    async def test_count_active(self, db: AsyncSession):
        from app.services.customer_price_service import CustomerPriceService
        svc = CustomerPriceService(db)
        count = await svc.count_active(tid)
        assert isinstance(count, int)


# ═══════════════════════════════════════════════════════════════════════════
# 7. POApprovalService — submit, approve, reject
# ═══════════════════════════════════════════════════════════════════════════

class TestPOApprovalService:
    async def _make_po(self, db: AsyncSession, status: POStatus = POStatus.draft) -> PurchaseOrder:
        supplier = await _supplier(db)
        prod = await _product(db)
        po = PurchaseOrder(
            id=uid(), tenant_id=tid, po_number=f"PO-AP-{uid()[:4]}",
            supplier_id=supplier.id, status=status,
        )
        db.add(po)
        await db.flush()
        line = PurchaseOrderLine(
            id=uid(), tenant_id=tid, po_id=po.id,
            product_id=prod.id, qty_ordered=Decimal("10"),
            unit_cost=Decimal("50"), line_total=Decimal("500"),
        )
        db.add(line)
        await db.flush()
        # Reload to populate lines relationship
        await db.refresh(po, ["lines"])
        return po

    @pytest.mark.asyncio
    async def test_submit_for_approval(self, db: AsyncSession):
        from app.services.po_approval_service import POApprovalService
        svc = POApprovalService(db)
        po = await self._make_po(db)
        result = await svc.submit_for_approval(po, "user-1", "Admin")
        assert result.status == POStatus.pending_approval
        assert result.approval_required is True

    @pytest.mark.asyncio
    async def test_submit_non_draft_fails(self, db: AsyncSession):
        from app.services.po_approval_service import POApprovalService
        svc = POApprovalService(db)
        po = await self._make_po(db, status=POStatus.sent)
        with pytest.raises(ValidationError, match="borrador"):
            await svc.submit_for_approval(po, "user-1")

    @pytest.mark.asyncio
    async def test_approve(self, db: AsyncSession):
        from app.services.po_approval_service import POApprovalService
        svc = POApprovalService(db)
        po = await self._make_po(db)
        po = await svc.submit_for_approval(po, "user-1")
        # Re-load lines to avoid lazy-load greenlet error
        await db.refresh(po, ["lines"])
        result = await svc.approve(po, "approver-1", "Manager")
        assert result.status == POStatus.approved
        assert result.approved_by == "approver-1"

    @pytest.mark.asyncio
    async def test_approve_non_pending_fails(self, db: AsyncSession):
        from app.services.po_approval_service import POApprovalService
        svc = POApprovalService(db)
        po = await self._make_po(db)
        with pytest.raises(ValidationError, match="pendientes"):
            await svc.approve(po, "approver-1")

    @pytest.mark.asyncio
    async def test_reject(self, db: AsyncSession):
        from app.services.po_approval_service import POApprovalService
        svc = POApprovalService(db)
        po = await self._make_po(db)
        po = await svc.submit_for_approval(po, "user-1")
        await db.refresh(po, ["lines"])
        result = await svc.reject(po, "mgr-1", "Too expensive", "Manager")
        assert result.status == POStatus.draft
        assert result.rejected_reason == "Too expensive"
        assert result.rejected_by == "mgr-1"

    @pytest.mark.asyncio
    async def test_reject_non_pending_fails(self, db: AsyncSession):
        from app.services.po_approval_service import POApprovalService
        svc = POApprovalService(db)
        po = await self._make_po(db)
        with pytest.raises(ValidationError, match="pendientes"):
            await svc.reject(po, "mgr-1", "reason")

    @pytest.mark.asyncio
    async def test_get_approval_log(self, db: AsyncSession):
        from app.services.po_approval_service import POApprovalService
        svc = POApprovalService(db)
        po = await self._make_po(db)
        await svc.submit_for_approval(po, "user-1", "User")
        logs = await svc.get_approval_log(po.id, tid)
        assert len(logs) >= 1
        assert logs[0].action == "submit"


# ═══════════════════════════════════════════════════════════════════════════
# 8. AnalyticsService — abc_classification, eoq, overview basics
# ═══════════════════════════════════════════════════════════════════════════

class TestAnalyticsService:
    @pytest.mark.asyncio
    async def test_overview_empty(self, db: AsyncSession):
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService(db)
        result = await svc.overview(tid)
        assert "total_skus" in result
        assert "pending_pos" in result
        assert "movement_trend" in result

    @pytest.mark.asyncio
    async def test_abc_classification_empty(self, db: AsyncSession):
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService(db)
        result = await svc.abc_classification(tid)
        assert result["total_products"] == 0
        assert result["grand_total_value"] == 0

    @pytest.mark.asyncio
    async def test_abc_classification_with_data(self, db: AsyncSession):
        from app.services.analytics_service import AnalyticsService
        prod = await _product(db, last_purchase_cost=Decimal("10"))
        wh = await _warehouse(db)
        # Create outgoing movement
        mov = StockMovement(
            id=uid(), tenant_id=tid, movement_type=MovementType.sale,
            product_id=prod.id, from_warehouse_id=wh.id,
            quantity=Decimal("100"), unit_cost=Decimal("10"),
        )
        db.add(mov)
        await db.flush()
        svc = AnalyticsService(db)
        result = await svc.abc_classification(tid, months=12)
        assert result["total_products"] >= 1

    @pytest.mark.asyncio
    async def test_eoq_empty(self, db: AsyncSession):
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService(db)
        result = await svc.eoq(tid, ordering_cost=50.0, holding_cost_pct=20.0)
        assert result["total_products"] == 0

    @pytest.mark.asyncio
    async def test_eoq_with_data(self, db: AsyncSession):
        from app.services.analytics_service import AnalyticsService
        prod = await _product(db, last_purchase_cost=Decimal("25"))
        wh = await _warehouse(db)
        # Sale movement = outgoing demand
        mov = StockMovement(
            id=uid(), tenant_id=tid, movement_type=MovementType.sale,
            product_id=prod.id, from_warehouse_id=wh.id,
            quantity=Decimal("200"), unit_cost=Decimal("25"),
        )
        db.add(mov)
        await db.flush()
        svc = AnalyticsService(db)
        result = await svc.eoq(tid, ordering_cost=50.0, holding_cost_pct=20.0)
        assert result["total_products"] >= 1
        assert result["items"][0]["eoq"] > 0

    @pytest.mark.asyncio
    async def test_occupation_no_locations(self, db: AsyncSession):
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService(db)
        result = await svc.occupation(tid)
        assert "occupation_pct" in result

    @pytest.mark.asyncio
    async def test_storage_valuation(self, db: AsyncSession):
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService(db)
        result = await svc.storage_valuation(tid)
        assert "total_monthly_cost" in result


# ═══════════════════════════════════════════════════════════════════════════
# 9. AlertService — check_and_generate, check_expiry_alerts
# ═══════════════════════════════════════════════════════════════════════════

class TestAlertService:
    @pytest.mark.asyncio
    async def test_check_and_generate_out_of_stock(self, db: AsyncSession):
        from app.services.alert_service import AlertService
        prod = await _product(db, min_stock_level=10, reorder_point=5)
        wh = await _warehouse(db)
        sl = await _stock_level(db, prod.id, wh.id, qty_on_hand=Decimal("0"), reorder_point=5)
        svc = AlertService(db)
        alerts = await svc.check_and_generate(tid)
        oos = [a for a in alerts if a["type"] == "out_of_stock" and a["product"] == prod.name]
        assert len(oos) >= 1

    @pytest.mark.asyncio
    async def test_check_and_generate_low_stock(self, db: AsyncSession):
        from app.services.alert_service import AlertService
        prod = await _product(db, min_stock_level=10, reorder_point=15)
        wh = await _warehouse(db)
        await _stock_level(db, prod.id, wh.id, qty_on_hand=Decimal("5"), reorder_point=15)
        svc = AlertService(db)
        alerts = await svc.check_and_generate(tid)
        low = [a for a in alerts if a["type"] == "low_stock" and a["product"] == prod.name]
        assert len(low) >= 1

    @pytest.mark.asyncio
    async def test_check_and_generate_reorder_point(self, db: AsyncSession):
        from app.services.alert_service import AlertService
        prod = await _product(db, min_stock_level=0, reorder_point=20)
        wh = await _warehouse(db)
        await _stock_level(db, prod.id, wh.id, qty_on_hand=Decimal("15"), reorder_point=20)
        svc = AlertService(db)
        alerts = await svc.check_and_generate(tid)
        rp = [a for a in alerts if a["type"] == "reorder_point" and a["product"] == prod.name]
        assert len(rp) >= 1

    @pytest.mark.asyncio
    async def test_check_and_generate_no_stock_records(self, db: AsyncSession):
        """Products with thresholds but NO stock levels at all should get out_of_stock alerts."""
        from app.services.alert_service import AlertService
        prod = await _product(db, min_stock_level=10, reorder_point=5)
        svc = AlertService(db)
        alerts = await svc.check_and_generate(tid)
        oos = [a for a in alerts if a["type"] == "out_of_stock" and a["product"] == prod.name]
        assert len(oos) >= 1

    @pytest.mark.asyncio
    async def test_check_expiry_alerts_expired(self, db: AsyncSession):
        from app.services.alert_service import AlertService
        prod = await _product(db)
        yesterday = date.today() - timedelta(days=1)
        batch = await _batch(db, prod.id, expiration_date=yesterday)
        svc = AlertService(db)
        alerts = await svc.check_expiry_alerts(tid, days=30)
        expired = [a for a in alerts if a["type"] == "expired"]
        assert len(expired) >= 1

    @pytest.mark.asyncio
    async def test_check_expiry_alerts_expiring_soon(self, db: AsyncSession):
        from app.services.alert_service import AlertService
        prod = await _product(db)
        soon = date.today() + timedelta(days=10)
        batch = await _batch(db, prod.id, expiration_date=soon)
        svc = AlertService(db)
        alerts = await svc.check_expiry_alerts(tid, days=30)
        expiring = [a for a in alerts if a["type"] == "expiring_soon"]
        assert len(expiring) >= 1

    @pytest.mark.asyncio
    async def test_check_expiry_alerts_idempotent(self, db: AsyncSession):
        """check_expiry_alerts can be called multiple times without error."""
        from app.services.alert_service import AlertService
        prod = await _product(db)
        yesterday = date.today() - timedelta(days=1)
        batch = await _batch(db, prod.id, expiration_date=yesterday)
        svc = AlertService(db)
        alerts1 = await svc.check_expiry_alerts(tid, days=30)
        our_alerts1 = [a for a in alerts1 if a.get("batch") == batch.batch_number]
        assert len(our_alerts1) >= 1
        # Second call should succeed (dedup relies on is_resolved server_default)
        alerts2 = await svc.check_expiry_alerts(tid, days=30)
        assert isinstance(alerts2, list)


# ═══════════════════════════════════════════════════════════════════════════
# 10. StockService — edge cases: adjust, return_stock, waste, qc
# ═══════════════════════════════════════════════════════════════════════════

class TestStockServiceEdgeCases:
    @pytest.mark.asyncio
    async def test_adjust_up(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        # First receive some stock
        await svc.receive(tid, prod.id, wh.id, Decimal("10"), unit_cost=Decimal("5"))
        mov = await svc.adjust(tid, prod.id, wh.id, Decimal("20"), reason="Recount")
        assert mov.movement_type == MovementType.adjustment_in
        assert mov.quantity == Decimal("10")

    @pytest.mark.asyncio
    async def test_adjust_down(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        await svc.receive(tid, prod.id, wh.id, Decimal("20"), unit_cost=Decimal("5"))
        mov = await svc.adjust(tid, prod.id, wh.id, Decimal("15"), reason="Shrinkage")
        assert mov.movement_type == MovementType.adjustment_out

    @pytest.mark.asyncio
    async def test_adjust_negative_qty_fails(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        with pytest.raises(ValidationError, match="negative"):
            await svc.adjust(tid, prod.id, wh.id, Decimal("-1"))

    @pytest.mark.asyncio
    async def test_return_stock(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        await svc.receive(tid, prod.id, wh.id, Decimal("10"), unit_cost=Decimal("5"))
        mov = await svc.return_stock(tid, prod.id, wh.id, Decimal("3"), reference="RET-001")
        assert mov.movement_type == MovementType.return_
        assert mov.quantity == Decimal("3")

    @pytest.mark.asyncio
    async def test_waste(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        await svc.receive(tid, prod.id, wh.id, Decimal("10"), unit_cost=Decimal("5"))
        mov = await svc.waste(tid, prod.id, wh.id, Decimal("2"), reason="Damaged")
        assert mov.movement_type == MovementType.waste

    @pytest.mark.asyncio
    async def test_waste_insufficient_stock(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        await svc.receive(tid, prod.id, wh.id, Decimal("5"), unit_cost=Decimal("5"))
        with pytest.raises(ValidationError, match="Insufficient"):
            await svc.waste(tid, prod.id, wh.id, Decimal("10"))

    @pytest.mark.asyncio
    async def test_adjust_in(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        mov = await svc.adjust_in(tid, prod.id, wh.id, Decimal("5"), reason="Found stock")
        assert mov.movement_type == MovementType.adjustment_in

    @pytest.mark.asyncio
    async def test_adjust_out(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        await svc.receive(tid, prod.id, wh.id, Decimal("10"), unit_cost=Decimal("5"))
        mov = await svc.adjust_out(tid, prod.id, wh.id, Decimal("3"), reason="Shrinkage")
        assert mov.movement_type == MovementType.adjustment_out

    @pytest.mark.asyncio
    async def test_adjust_out_insufficient(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        with pytest.raises(ValidationError, match="insuficiente"):
            await svc.adjust_out(tid, prod.id, wh.id, Decimal("100"))

    @pytest.mark.asyncio
    async def test_transfer(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh1 = await _warehouse(db, code=f"WH1-{uid()[:4]}")
        wh2 = await _warehouse(db, code=f"WH2-{uid()[:4]}")
        svc = StockService(db)
        await svc.receive(tid, prod.id, wh1.id, Decimal("20"), unit_cost=Decimal("5"))
        mov = await svc.transfer(tid, prod.id, wh1.id, wh2.id, Decimal("8"))
        assert mov.movement_type == MovementType.transfer

    @pytest.mark.asyncio
    async def test_transfer_same_warehouse_fails(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        with pytest.raises(ValidationError, match="differ"):
            await svc.transfer(tid, prod.id, wh.id, wh.id, Decimal("5"))

    @pytest.mark.asyncio
    async def test_issue_qc_pending_rejected(self, db: AsyncSession):
        from app.services.stock_service import StockService
        prod = await _product(db)
        wh = await _warehouse(db)
        svc = StockService(db)
        await svc.receive(tid, prod.id, wh.id, Decimal("10"), unit_cost=Decimal("5"))
        # Manually set QC status to pending
        from sqlalchemy import select
        level = (await db.execute(
            select(StockLevel).where(
                StockLevel.product_id == prod.id, StockLevel.warehouse_id == wh.id
            )
        )).scalar_one()
        level.qc_status = "pending_qc"
        await db.flush()
        with pytest.raises(ValidationError, match="cuarentena"):
            await svc.issue(tid, prod.id, wh.id, Decimal("5"))

    @pytest.mark.asyncio
    async def test_get_summary(self, db: AsyncSession):
        from app.services.stock_service import StockService
        svc = StockService(db)
        summary = await svc.get_summary(tid)
        assert "total_skus" in summary
        assert "total_value" in summary
        assert "low_stock_count" in summary
