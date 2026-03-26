"""Miscellaneous coverage tests — cost_service, po_notification_service,
pdf_report_service, pnl_analysis schemas, portal_service, variant_service,
batch_service, serial_service."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Category,
    Customer,
    Product,
    ProductVariant,
    SalesOrder,
    SalesOrderLine,
    StockLayer,
    StockLevel,
    StockMovement,
    VariantAttribute,
    VariantAttributeOption,
    Warehouse,
)
from app.db.models.enums import MovementType, SalesOrderStatus
from app.db.models.tracking import EntityBatch, EntitySerial, SerialStatus

uid = lambda: str(uuid.uuid4())
tid = "test-tenant"


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _mk_category(db: AsyncSession, **kw) -> Category:
    obj = Category(id=uid(), tenant_id=tid, name=kw.get("name", f"Cat-{uid()[:6]}"),
                   slug=kw.get("slug", f"cat-{uid()[:6]}"))
    db.add(obj)
    await db.flush()
    return obj


async def _mk_product(db: AsyncSession, **kw) -> Product:
    obj = Product(id=kw.get("id", uid()), tenant_id=tid,
                  sku=kw.get("sku", f"SKU-{uid()[:8]}"),
                  name=kw.get("name", f"Prod-{uid()[:6]}"))
    db.add(obj)
    await db.flush()
    return obj


async def _mk_warehouse(db: AsyncSession, **kw) -> Warehouse:
    obj = Warehouse(id=kw.get("id", uid()), tenant_id=tid,
                    name=kw.get("name", f"WH-{uid()[:6]}"),
                    code=kw.get("code", f"WH-{uid()[:6]}"))
    db.add(obj)
    await db.flush()
    return obj


async def _mk_customer(db: AsyncSession, **kw) -> Customer:
    obj = Customer(id=kw.get("id", uid()), tenant_id=tid,
                   name=kw.get("name", f"Cust-{uid()[:6]}"),
                   code=kw.get("code", f"C-{uid()[:6]}"))
    db.add(obj)
    await db.flush()
    return obj


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CostService
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cost_create_layer(db: AsyncSession):
    from app.services.cost_service import CostService
    p = await _mk_product(db)
    w = await _mk_warehouse(db)
    svc = CostService(db)
    layer = await svc.create_layer(tid, p.id, w.id, Decimal("10"), Decimal("500"))
    assert layer.quantity_initial == Decimal("10")
    assert layer.unit_cost == Decimal("500")


@pytest.mark.asyncio
async def test_cost_consume_fifo(db: AsyncSession):
    from app.services.cost_service import CostService
    p = await _mk_product(db)
    w = await _mk_warehouse(db)
    svc = CostService(db)
    await svc.create_layer(tid, p.id, w.id, Decimal("5"), Decimal("100"))
    await svc.create_layer(tid, p.id, w.id, Decimal("5"), Decimal("200"))
    total_cost = await svc.consume_fifo(p.id, w.id, Decimal("7"))
    # First 5 @ 100 = 500, next 2 @ 200 = 400 → 900
    assert total_cost == Decimal("900")


@pytest.mark.asyncio
async def test_cost_weighted_average(db: AsyncSession):
    from app.services.cost_service import CostService
    p = await _mk_product(db)
    w = await _mk_warehouse(db)
    svc = CostService(db)
    await svc.create_layer(tid, p.id, w.id, Decimal("10"), Decimal("100"))
    await svc.create_layer(tid, p.id, w.id, Decimal("10"), Decimal("200"))
    avg = await svc.get_weighted_average_cost(p.id, w.id)
    assert avg == Decimal("150")


@pytest.mark.asyncio
async def test_cost_weighted_average_no_layers(db: AsyncSession):
    from app.services.cost_service import CostService
    p = await _mk_product(db)
    w = await _mk_warehouse(db)
    svc = CostService(db)
    avg = await svc.get_weighted_average_cost(p.id, w.id)
    assert avg == Decimal("0")


@pytest.mark.asyncio
async def test_cost_list_layers(db: AsyncSession):
    from app.services.cost_service import CostService
    p = await _mk_product(db)
    w = await _mk_warehouse(db)
    svc = CostService(db)
    await svc.create_layer(tid, p.id, w.id, Decimal("3"), Decimal("50"))
    layers = await svc.list_layers(tid, p.id)
    assert len(layers) >= 1

    layers_wh = await svc.list_layers(tid, p.id, w.id)
    assert len(layers_wh) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PONotificationService
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_po_notify_margin_danger(db: AsyncSession):
    from app.services.po_notification_service import PONotificationService
    svc = PONotificationService(db)
    # Should not raise — it logs + creates audit entry
    await svc.notify_margin_danger(
        tenant_id=tid,
        product_name="Leche",
        product_sku="LECHE-001",
        new_cost=5000.0,
        actual_margin=15.0,
        minimum_margin=20.0,
        po_number="PO-2026-0001",
    )


@pytest.mark.asyncio
async def test_po_notify_po_sent(db: AsyncSession):
    from app.services.po_notification_service import PONotificationService
    svc = PONotificationService(db)
    await svc.notify_po_sent(tid, "PO-2026-0002", "Proveedor A", "a@example.com")


@pytest.mark.asyncio
async def test_po_notify_po_approved(db: AsyncSession):
    from app.services.po_notification_service import PONotificationService
    svc = PONotificationService(db)
    await svc.notify_po_approved(tid, "PO-2026-0003", "Admin User")


@pytest.mark.asyncio
async def test_po_notify_po_rejected(db: AsyncSession):
    from app.services.po_notification_service import PONotificationService
    svc = PONotificationService(db)
    await svc.notify_po_rejected(tid, "PO-2026-0004", "Admin User", "Too expensive")


@pytest.mark.asyncio
async def test_po_notify_send_fails_gracefully(db: AsyncSession):
    """_send should catch HTTP errors and just warn."""
    from app.services.po_notification_service import PONotificationService
    svc = PONotificationService(db)
    with patch("app.services.po_notification_service.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client
        # Should not raise
        await svc._send(tid, "x@test.com", "test", {"key": "val"})


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PDF Report Service
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_pdf_generate_empty():
    try:
        from app.services.pdf_report_service import generate_pnl_pdf
    except ImportError:
        pytest.skip("reportlab not installed")

    pdf_bytes = generate_pnl_pdf({"totals": {}, "products": []}, tenant_name="TestCo")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 100
    assert pdf_bytes[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_pdf_generate_with_products():
    try:
        from app.services.pdf_report_service import generate_pnl_pdf
    except ImportError:
        pytest.skip("reportlab not installed")

    data = {
        "totals": {
            "product_count": 2,
            "total_purchased_cost": 100000,
            "total_revenue": 200000,
            "gross_profit": 100000,
            "gross_margin_pct": 50.0,
            "total_cogs": 100000,
            "stock_current_value": 50000,
        },
        "products": [
            {
                "product_name": "Widget A",
                "product_sku": "WA-001",
                "summary": {
                    "total_revenue": 120000,
                    "total_cogs": 60000,
                    "gross_profit": 60000,
                    "gross_margin_pct": 50.0,
                    "margin_target": 35.0,
                },
            },
            {
                "product_name": "Widget B",
                "product_sku": "WB-002",
                "summary": {
                    "total_revenue": 80000,
                    "total_cogs": 40000,
                    "gross_profit": 40000,
                    "gross_margin_pct": 50.0,
                    "margin_target": 30.0,
                },
            },
        ],
    }
    pdf_bytes = generate_pnl_pdf(data, "MyCo")
    assert pdf_bytes[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_pdf_cop_helper():
    try:
        from app.services.pdf_report_service import _cop, _pct
    except ImportError:
        pytest.skip("reportlab not installed")

    assert "$" in _cop(1500)
    assert _cop(-500).startswith("-$")
    assert _cop(0) == "$0"
    assert _cop(None) == "$0"
    assert "%" in _pct(33.3)
    assert _pct(None) == "0.0%"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PnL Analysis Schemas
# ═══════════════════════════════════════════════════════════════════════════════

def test_pnl_alert_schema():
    from app.domain.schemas.pnl_analysis import PnLAlert
    a = PnLAlert(titulo="Test", detalle="Detail", severidad="alta", producto_sku="SKU-1")
    assert a.severidad == "alta"
    assert a.producto_sku == "SKU-1"


def test_pnl_alert_no_sku():
    from app.domain.schemas.pnl_analysis import PnLAlert
    a = PnLAlert(titulo="Alert", detalle="Details", severidad="baja")
    assert a.producto_sku is None


def test_pnl_oportunidad_schema():
    from app.domain.schemas.pnl_analysis import PnLOportunidad
    o = PnLOportunidad(titulo="Op", detalle="Info", impacto_estimado="$10M", producto_sku="X")
    assert o.impacto_estimado == "$10M"


def test_pnl_producto_estrella():
    from app.domain.schemas.pnl_analysis import PnLProductoEstrella
    p = PnLProductoEstrella(sku="STAR-1", nombre="Top Seller", razon="High margin")
    assert p.sku == "STAR-1"


def test_pnl_recomendacion():
    from app.domain.schemas.pnl_analysis import PnLRecomendacion
    r = PnLRecomendacion(accion="Buy more", prioridad="media", plazo="esta_semana")
    assert r.plazo == "esta_semana"

    r2 = PnLRecomendacion(accion="Sell", prioridad="alta")
    assert r2.plazo is None


def test_pnl_analysis_full():
    from app.domain.schemas.pnl_analysis import PnLAnalysis, PnLAlert, PnLRecomendacion
    a = PnLAnalysis(
        resumen="Good month",
        alertas=[PnLAlert(titulo="x", detalle="y", severidad="media")],
        recomendaciones=[PnLRecomendacion(accion="a", prioridad="baja")],
        is_cached=True,
        cache_source="session_cache",
    )
    assert a.is_cached is True
    assert a.cache_source == "session_cache"
    assert len(a.alertas) == 1


def test_pnl_analysis_defaults():
    from app.domain.schemas.pnl_analysis import PnLAnalysis
    a = PnLAnalysis(resumen="Minimal")
    assert a.alertas == []
    assert a.oportunidades == []
    assert a.productos_estrella == []
    assert a.recomendaciones == []
    assert a.is_cached is False
    assert a.cached_at is None
    assert a.cache_source == "fresh"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PortalService
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_portal_customer_stock_empty(db: AsyncSession):
    from app.services.portal_service import PortalService
    svc = PortalService(db)
    result = await svc.get_customer_stock(tid, uid())
    assert result == []


@pytest.mark.asyncio
async def test_portal_customer_stock_with_data(db: AsyncSession):
    from app.services.portal_service import PortalService
    p = await _mk_product(db)
    w = await _mk_warehouse(db)
    c = await _mk_customer(db)

    # Create stock level
    sl = StockLevel(id=uid(), tenant_id=tid, product_id=p.id, warehouse_id=w.id,
                    qty_on_hand=Decimal("100"), qty_reserved=Decimal("0"))
    db.add(sl)

    # Create sales order + line referencing the product
    so = SalesOrder(id=uid(), tenant_id=tid, order_number=f"SO-{uid()[:6]}",
                    customer_id=c.id, status=SalesOrderStatus.draft,
                    subtotal=Decimal("0"), tax_amount=Decimal("0"),
                    discount_amount=Decimal("0"), total=Decimal("0"))
    db.add(so)
    await db.flush()

    sol = SalesOrderLine(id=uid(), tenant_id=tid, order_id=so.id, product_id=p.id,
                         qty_ordered=Decimal("10"), qty_shipped=Decimal("0"),
                         unit_price=Decimal("100"), tax_rate=Decimal("0"),
                         line_total=Decimal("1000"))
    db.add(sol)
    await db.flush()

    svc = PortalService(db)
    result = await svc.get_customer_stock(tid, c.id)
    assert len(result) >= 1
    assert result[0]["product_id"] == p.id


@pytest.mark.asyncio
async def test_portal_customer_orders(db: AsyncSession):
    from app.services.portal_service import PortalService
    p = await _mk_product(db)
    c = await _mk_customer(db)

    so = SalesOrder(id=uid(), tenant_id=tid, order_number=f"SO-{uid()[:6]}",
                    customer_id=c.id, status=SalesOrderStatus.draft,
                    subtotal=Decimal("500"), tax_amount=Decimal("50"),
                    discount_amount=Decimal("0"), total=Decimal("550"))
    db.add(so)
    await db.flush()

    sol = SalesOrderLine(id=uid(), tenant_id=tid, order_id=so.id, product_id=p.id,
                         qty_ordered=Decimal("5"), qty_shipped=Decimal("0"),
                         unit_price=Decimal("100"), tax_rate=Decimal("0"),
                         line_total=Decimal("500"))
    db.add(sol)
    await db.flush()

    svc = PortalService(db)
    orders = await svc.get_customer_orders(tid, c.id)
    assert len(orders) >= 1
    assert orders[0]["order_number"] == so.order_number


@pytest.mark.asyncio
async def test_portal_customer_orders_filter_status(db: AsyncSession):
    from app.services.portal_service import PortalService
    c = await _mk_customer(db)
    svc = PortalService(db)
    # Filter with an invalid status — should just ignore it
    orders = await svc.get_customer_orders(tid, c.id, status="nonexistent_status")
    assert isinstance(orders, list)


@pytest.mark.asyncio
async def test_portal_order_detail(db: AsyncSession):
    from app.services.portal_service import PortalService
    p = await _mk_product(db)
    c = await _mk_customer(db)

    so = SalesOrder(id=uid(), tenant_id=tid, order_number=f"SO-{uid()[:6]}",
                    customer_id=c.id, status=SalesOrderStatus.draft,
                    subtotal=Decimal("500"), tax_amount=Decimal("50"),
                    discount_amount=Decimal("0"), total=Decimal("550"))
    db.add(so)
    await db.flush()

    sol = SalesOrderLine(id=uid(), tenant_id=tid, order_id=so.id, product_id=p.id,
                         qty_ordered=Decimal("5"), qty_shipped=Decimal("0"),
                         unit_price=Decimal("100"), tax_rate=Decimal("0"),
                         line_total=Decimal("500"))
    db.add(sol)
    await db.flush()

    svc = PortalService(db)
    detail = await svc.get_order_detail(tid, so.id, c.id)
    assert detail["id"] == so.id
    assert len(detail["lines"]) == 1
    assert detail["lines"][0]["product_id"] == p.id


@pytest.mark.asyncio
async def test_portal_order_detail_not_found(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.portal_service import PortalService
    c = await _mk_customer(db)
    svc = PortalService(db)
    with pytest.raises(NotFoundError):
        await svc.get_order_detail(tid, uid(), c.id)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. VariantService
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_variant_create_attribute(db: AsyncSession):
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    attr = await svc.create_attribute(tid, {"name": "Color", "slug": f"color-{uid()[:6]}"})
    assert attr.name == "Color"


@pytest.mark.asyncio
async def test_variant_create_attribute_with_options(db: AsyncSession):
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    attr = await svc.create_attribute(
        tid,
        {"name": "Size", "slug": f"size-{uid()[:6]}"},
        options=[{"value": "S"}, {"value": "M"}],
    )
    assert attr.name == "Size"


@pytest.mark.asyncio
async def test_variant_list_attributes(db: AsyncSession):
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    result = await svc.list_attributes(tid)
    assert isinstance(result, (list, tuple)) or hasattr(result, "__iter__")


@pytest.mark.asyncio
async def test_variant_update_attribute(db: AsyncSession):
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    attr = await svc.create_attribute(tid, {"name": "Material", "slug": f"mat-{uid()[:6]}"})
    updated = await svc.update_attribute(attr.id, tid, {"name": "Fabric"})
    assert updated.name == "Fabric"


@pytest.mark.asyncio
async def test_variant_update_attribute_not_found(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    with pytest.raises(NotFoundError):
        await svc.update_attribute(uid(), tid, {"name": "X"})


@pytest.mark.asyncio
async def test_variant_delete_attribute(db: AsyncSession):
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    attr = await svc.create_attribute(tid, {"name": "Flavor", "slug": f"flv-{uid()[:6]}"})
    await svc.delete_attribute(attr.id, tid)


@pytest.mark.asyncio
async def test_variant_delete_attribute_not_found(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    with pytest.raises(NotFoundError):
        await svc.delete_attribute(uid(), tid)


@pytest.mark.asyncio
async def test_variant_add_option(db: AsyncSession):
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    attr = await svc.create_attribute(tid, {"name": "Weight", "slug": f"wgt-{uid()[:6]}"})
    opt = await svc.add_option(attr.id, tid, {"value": "100g"})
    assert opt.value == "100g"


@pytest.mark.asyncio
async def test_variant_add_option_attr_not_found(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    with pytest.raises(NotFoundError):
        await svc.add_option(uid(), tid, {"value": "X"})


@pytest.mark.asyncio
async def test_variant_crud_product_variant(db: AsyncSession):
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    p = await _mk_product(db)
    v = await svc.create_variant(tid, {
        "parent_id": p.id, "sku": f"VAR-{uid()[:8]}",
        "name": "Red XL", "cost_price": Decimal("100"), "sale_price": Decimal("200"),
        "option_values": {}, "images": [],
    })
    assert v.name == "Red XL"

    # get
    fetched = await svc.get_variant(v.id, tid)
    assert fetched.id == v.id

    # update
    updated = await svc.update_variant(v.id, tid, {"name": "Blue XL"})
    assert updated.name == "Blue XL"

    # delete
    await svc.delete_variant(v.id, tid)


@pytest.mark.asyncio
async def test_variant_create_variant_parent_not_found(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    with pytest.raises(NotFoundError):
        await svc.create_variant(tid, {"parent_id": uid(), "sku": "X", "name": "X"})


@pytest.mark.asyncio
async def test_variant_get_variant_not_found(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    with pytest.raises(NotFoundError):
        await svc.get_variant(uid(), tid)


@pytest.mark.asyncio
async def test_variant_list_variants_for_product(db: AsyncSession):
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    p = await _mk_product(db)
    result = await svc.list_variants_for_product(p.id, tid)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_variant_list_variants_for_missing_product(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.variant_service import VariantService
    svc = VariantService(db)
    with pytest.raises(NotFoundError):
        await svc.list_variants_for_product(uid(), tid)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. BatchService
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_batch_create(db: AsyncSession):
    from app.services.batch_service import BatchService
    p = await _mk_product(db)
    svc = BatchService(db)
    batch = await svc.create(tid, {
        "entity_id": p.id, "batch_number": f"LOT-{uid()[:6]}",
        "quantity": Decimal("100"),
        "metadata": {"origin": "farm"},
    })
    assert batch.batch_number.startswith("LOT-")


@pytest.mark.asyncio
async def test_batch_get(db: AsyncSession):
    from app.services.batch_service import BatchService
    p = await _mk_product(db)
    svc = BatchService(db)
    batch = await svc.create(tid, {
        "entity_id": p.id, "batch_number": f"LOT-{uid()[:6]}",
        "quantity": Decimal("50"),
    })
    fetched = await svc.get(tid, batch.id)
    assert fetched.id == batch.id


@pytest.mark.asyncio
async def test_batch_get_not_found(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.batch_service import BatchService
    svc = BatchService(db)
    with pytest.raises(NotFoundError):
        await svc.get(tid, uid())


@pytest.mark.asyncio
async def test_batch_update(db: AsyncSession):
    from app.services.batch_service import BatchService
    p = await _mk_product(db)
    svc = BatchService(db)
    batch = await svc.create(tid, {
        "entity_id": p.id, "batch_number": f"LOT-{uid()[:6]}",
        "quantity": Decimal("20"),
    })
    updated = await svc.update(tid, batch.id, {"notes": "updated", "metadata": {"x": 1}})
    assert updated.notes == "updated"


@pytest.mark.asyncio
async def test_batch_update_not_found(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.batch_service import BatchService
    svc = BatchService(db)
    with pytest.raises(NotFoundError):
        await svc.update(tid, uid(), {"notes": "x"})


@pytest.mark.asyncio
async def test_batch_delete(db: AsyncSession):
    from app.services.batch_service import BatchService
    p = await _mk_product(db)
    svc = BatchService(db)
    batch = await svc.create(tid, {
        "entity_id": p.id, "batch_number": f"LOT-{uid()[:6]}",
        "quantity": Decimal("10"),
    })
    await svc.delete(tid, batch.id)


@pytest.mark.asyncio
async def test_batch_list(db: AsyncSession):
    from app.services.batch_service import BatchService
    p = await _mk_product(db)
    svc = BatchService(db)
    await svc.create(tid, {
        "entity_id": p.id, "batch_number": f"LOT-{uid()[:6]}",
        "quantity": Decimal("5"),
    })
    result = await svc.list(tid)
    assert hasattr(result, "items") or isinstance(result, (list, tuple))


@pytest.mark.asyncio
async def test_batch_list_expiring(db: AsyncSession):
    from app.services.batch_service import BatchService
    p = await _mk_product(db)
    svc = BatchService(db)
    result = await svc.list_expiring(tid, days=30)
    assert hasattr(result, "items") or isinstance(result, (list, tuple))


@pytest.mark.asyncio
async def test_batch_search(db: AsyncSession):
    from app.services.batch_service import BatchService
    p = await _mk_product(db)
    code = f"SRCH-{uid()[:6]}"
    svc = BatchService(db)
    await svc.create(tid, {
        "entity_id": p.id, "batch_number": code,
        "quantity": Decimal("10"),
    })
    results = await svc.search(tid, code)
    assert len(results) >= 1
    assert results[0].batch.batch_number == code


@pytest.mark.asyncio
async def test_batch_search_with_expiration(db: AsyncSession):
    """Test batch search with expiration_date to cover expiry status branches."""
    from app.services.batch_service import BatchService
    p = await _mk_product(db)
    code = f"EXP-{uid()[:6]}"
    svc = BatchService(db)
    # Expired batch
    await svc.create(tid, {
        "entity_id": p.id, "batch_number": code,
        "quantity": Decimal("5"),
        "expiration_date": date(2020, 1, 1),
    })
    results = await svc.search(tid, code)
    assert len(results) >= 1
    assert results[0].expiration_status == "expired"


@pytest.mark.asyncio
async def test_batch_trace_forward(db: AsyncSession):
    from app.services.batch_service import BatchService
    p = await _mk_product(db)
    svc = BatchService(db)
    batch = await svc.create(tid, {
        "entity_id": p.id, "batch_number": f"TF-{uid()[:6]}",
        "quantity": Decimal("50"),
    })
    result = await svc.trace_forward(tid, batch.id)
    assert result.batch.id == batch.id
    assert result.product_id == p.id
    assert result.dispatches == []


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SerialService
# ═══════════════════════════════════════════════════════════════════════════════

async def _mk_serial_status(db: AsyncSession, **kw) -> SerialStatus:
    obj = SerialStatus(id=uid(), tenant_id=tid,
                       name=kw.get("name", f"Status-{uid()[:6]}"),
                       slug=kw.get("slug", f"st-{uid()[:6]}"))
    db.add(obj)
    await db.flush()
    return obj


@pytest.mark.asyncio
async def test_serial_create(db: AsyncSession):
    from app.services.serial_service import SerialService
    p = await _mk_product(db)
    st = await _mk_serial_status(db)
    svc = SerialService(db)
    serial = await svc.create(tid, {
        "entity_id": p.id, "serial_number": f"SN-{uid()[:8]}",
        "status_id": st.id,
        "metadata": {"batch": "A"},
    })
    assert serial.serial_number.startswith("SN-")


@pytest.mark.asyncio
async def test_serial_get(db: AsyncSession):
    from app.services.serial_service import SerialService
    p = await _mk_product(db)
    st = await _mk_serial_status(db)
    svc = SerialService(db)
    serial = await svc.create(tid, {
        "entity_id": p.id, "serial_number": f"SN-{uid()[:8]}",
        "status_id": st.id,
    })
    fetched = await svc.get(tid, serial.id)
    assert fetched.id == serial.id


@pytest.mark.asyncio
async def test_serial_get_not_found(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.serial_service import SerialService
    svc = SerialService(db)
    with pytest.raises(NotFoundError):
        await svc.get(tid, uid())


@pytest.mark.asyncio
async def test_serial_update(db: AsyncSession):
    from app.services.serial_service import SerialService
    p = await _mk_product(db)
    st = await _mk_serial_status(db)
    svc = SerialService(db)
    serial = await svc.create(tid, {
        "entity_id": p.id, "serial_number": f"SN-{uid()[:8]}",
        "status_id": st.id,
    })
    updated = await svc.update(tid, serial.id, {"notes": "repaired", "metadata": {"x": 1}})
    assert updated.notes == "repaired"


@pytest.mark.asyncio
async def test_serial_update_not_found(db: AsyncSession):
    from app.core.errors import NotFoundError
    from app.services.serial_service import SerialService
    svc = SerialService(db)
    with pytest.raises(NotFoundError):
        await svc.update(tid, uid(), {"notes": "x"})


@pytest.mark.asyncio
async def test_serial_delete(db: AsyncSession):
    from app.services.serial_service import SerialService
    p = await _mk_product(db)
    st = await _mk_serial_status(db)
    svc = SerialService(db)
    serial = await svc.create(tid, {
        "entity_id": p.id, "serial_number": f"SN-{uid()[:8]}",
        "status_id": st.id,
    })
    await svc.delete(tid, serial.id)


@pytest.mark.asyncio
async def test_serial_list(db: AsyncSession):
    from app.services.serial_service import SerialService
    svc = SerialService(db)
    result = await svc.list(tid)
    assert hasattr(result, "items") or isinstance(result, (list, tuple))
