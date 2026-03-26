"""Unit tests for SalesOrderService — exercises service methods directly via db fixture."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models import Product, Warehouse
from app.db.models.customer import Customer
from app.db.models.enums import SalesOrderStatus
from app.db.models.sales_order import SalesOrder, SalesOrderLine
from app.db.models.stock import StockLevel
from app.services.sales_order_service import (
    SalesOrderService,
    VALID_TRANSITIONS,
    recalculate_so_totals,
)

uid = lambda: str(uuid.uuid4())
TID = "test-tenant"


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _make_product(db: AsyncSession, sku: str = "SOU-P", name: str = "Test Product") -> Product:
    p = Product(
        id=uid(), tenant_id=TID, sku=sku, name=name, unit_of_measure="un",
        last_purchase_cost=Decimal("10000"), suggested_sale_price=Decimal("15000"),
    )
    db.add(p)
    await db.flush()
    return p


async def _make_warehouse(db: AsyncSession, code: str = "SOU-WH") -> Warehouse:
    w = Warehouse(id=uid(), tenant_id=TID, name=f"WH-{code}", code=code, type="main")
    db.add(w)
    await db.flush()
    return w


async def _make_customer(db: AsyncSession, code: str = "SOU-C") -> Customer:
    c = Customer(id=uid(), tenant_id=TID, name=f"Customer-{code}", code=code, is_active=True)
    db.add(c)
    await db.flush()
    return c


async def _add_stock(
    db: AsyncSession, product_id: str, warehouse_id: str, qty: Decimal = Decimal("100"),
) -> StockLevel:
    sl = StockLevel(
        id=uid(), tenant_id=TID, product_id=product_id, warehouse_id=warehouse_id,
        qty_on_hand=qty, qty_reserved=Decimal("0"),
    )
    db.add(sl)
    await db.flush()
    return sl


async def _create_draft_so(
    db: AsyncSession,
    customer_id: str,
    warehouse_id: str,
    product_id: str,
    qty: float = 10,
    unit_price: float = 15000,
) -> SalesOrder:
    """Create a draft SO through the service, patching out price/tax sub-services."""
    svc = SalesOrderService(db)
    with patch("app.services.customer_price_service.CustomerPriceService.get_customer_price",
               new_callable=AsyncMock, return_value=None), \
         patch("app.services.tax_service.TaxService.get_product_tax_rate",
               new_callable=AsyncMock, return_value=(Decimal("0"), None)):
        so = await svc.create(
            tenant_id=TID,
            data={"customer_id": customer_id, "warehouse_id": warehouse_id},
            lines=[{"product_id": product_id, "qty_ordered": qty, "unit_price": unit_price}],
            user_id="test-user",
        )
    return so


async def _fast_transition(db: AsyncSession, so: SalesOrder, target: SalesOrderStatus):
    """Forcefully set status (bypass service validations) for test setup."""
    so.status = target
    await db.flush()


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_draft_so(db: AsyncSession):
    """Create a draft SO and verify basic fields."""
    p = await _make_product(db, sku="SOU-C1")
    w = await _make_warehouse(db, code="SOU-C1")
    c = await _make_customer(db, code="SOU-C1")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)

    assert so.status == SalesOrderStatus.draft
    assert so.customer_id == c.id
    assert so.order_number.startswith("SO-")
    assert len(so.lines) == 1
    assert so.lines[0].qty_ordered == Decimal("10")


@pytest.mark.asyncio
async def test_create_so_no_customer_raises(db: AsyncSession):
    """Creating SO with non-existent customer raises NotFoundError."""
    p = await _make_product(db, sku="SOU-NC1")
    w = await _make_warehouse(db, code="SOU-NC1")

    svc = SalesOrderService(db)
    with pytest.raises(NotFoundError, match="Customer not found"):
        await svc.create(
            TID,
            data={"customer_id": uid(), "warehouse_id": w.id},
            lines=[{"product_id": p.id, "qty_ordered": 5, "unit_price": 1000}],
        )


@pytest.mark.asyncio
async def test_create_so_no_lines_raises(db: AsyncSession):
    """Creating SO with empty lines raises ValidationError."""
    c = await _make_customer(db, code="SOU-NL1")
    w = await _make_warehouse(db, code="SOU-NL1")

    svc = SalesOrderService(db)
    with pytest.raises(ValidationError, match="al menos una línea"):
        await svc.create(TID, data={"customer_id": c.id, "warehouse_id": w.id}, lines=[])


@pytest.mark.asyncio
async def test_create_so_invalid_qty_raises(db: AsyncSession):
    """Line with qty <= 0 raises ValidationError."""
    p = await _make_product(db, sku="SOU-IQ1")
    w = await _make_warehouse(db, code="SOU-IQ1")
    c = await _make_customer(db, code="SOU-IQ1")

    svc = SalesOrderService(db)
    with pytest.raises(ValidationError, match="cantidad es obligatoria"):
        await svc.create(
            TID,
            data={"customer_id": c.id, "warehouse_id": w.id},
            lines=[{"product_id": p.id, "qty_ordered": 0, "unit_price": 1000}],
        )


@pytest.mark.asyncio
async def test_create_so_negative_price_raises(db: AsyncSession):
    """Line with negative unit price raises ValidationError."""
    p = await _make_product(db, sku="SOU-NP1")
    w = await _make_warehouse(db, code="SOU-NP1")
    c = await _make_customer(db, code="SOU-NP1")

    svc = SalesOrderService(db)
    with pytest.raises(ValidationError, match="precio unitario no puede ser negativo"):
        await svc.create(
            TID,
            data={"customer_id": c.id, "warehouse_id": w.id},
            lines=[{"product_id": p.id, "qty_ordered": 5, "unit_price": -100}],
        )


@pytest.mark.asyncio
async def test_create_so_product_not_found_raises(db: AsyncSession):
    """Line referencing non-existent product raises NotFoundError."""
    w = await _make_warehouse(db, code="SOU-PNF")
    c = await _make_customer(db, code="SOU-PNF")

    svc = SalesOrderService(db)
    with patch("app.services.customer_price_service.CustomerPriceService.get_customer_price",
               new_callable=AsyncMock, return_value=None), \
         patch("app.services.tax_service.TaxService.get_product_tax_rate",
               new_callable=AsyncMock, return_value=(Decimal("0"), None)):
        with pytest.raises(NotFoundError, match="not found"):
            await svc.create(
                TID,
                data={"customer_id": c.id, "warehouse_id": w.id},
                lines=[{"product_id": uid(), "qty_ordered": 5, "unit_price": 1000}],
            )


@pytest.mark.asyncio
async def test_get_existing_so(db: AsyncSession):
    """get() returns a valid SO by id."""
    p = await _make_product(db, sku="SOU-G1")
    w = await _make_warehouse(db, code="SOU-G1")
    c = await _make_customer(db, code="SOU-G1")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    svc = SalesOrderService(db)
    fetched = await svc.get(so.id, TID)
    assert fetched.id == so.id


@pytest.mark.asyncio
async def test_get_not_found_raises(db: AsyncSession):
    """get() with non-existent id raises NotFoundError."""
    svc = SalesOrderService(db)
    with pytest.raises(NotFoundError, match="not found"):
        await svc.get(uid(), TID)


@pytest.mark.asyncio
async def test_list_empty(db: AsyncSession):
    """list() on a tenant with no orders returns empty tuple."""
    svc = SalesOrderService(db)
    orders, total = await svc.list("nonexistent-tenant-xyz")
    assert orders == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_with_status_filter(db: AsyncSession):
    """list() filters by status correctly."""
    p = await _make_product(db, sku="SOU-LS1")
    w = await _make_warehouse(db, code="SOU-LS1")
    c = await _make_customer(db, code="SOU-LS1")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)

    svc = SalesOrderService(db)
    drafts, count = await svc.list(TID, status="draft")
    ids = [o.id for o in drafts]
    assert so.id in ids

    confirmed, c2 = await svc.list(TID, status="confirmed")
    ids2 = [o.id for o in confirmed]
    assert so.id not in ids2


@pytest.mark.asyncio
async def test_list_with_customer_filter(db: AsyncSession):
    """list() filters by customer_id correctly."""
    p = await _make_product(db, sku="SOU-LC1")
    w = await _make_warehouse(db, code="SOU-LC1")
    c1 = await _make_customer(db, code="SOU-LC1A")
    c2 = await _make_customer(db, code="SOU-LC1B")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c1.id, w.id, p.id)

    svc = SalesOrderService(db)
    results, _ = await svc.list(TID, customer_id=c1.id)
    assert any(o.id == so.id for o in results)

    results2, _ = await svc.list(TID, customer_id=c2.id)
    assert not any(o.id == so.id for o in results2)


@pytest.mark.asyncio
async def test_delete_draft_so(db: AsyncSession):
    """delete() on a draft SO completes without error (validates draft check passes)."""
    p = await _make_product(db, sku="SOU-DD1")
    w = await _make_warehouse(db, code="SOU-DD1")
    c = await _make_customer(db, code="SOU-DD1")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    svc = SalesOrderService(db)
    # Should not raise — draft orders are deletable
    await svc.delete(so.id, TID)


@pytest.mark.asyncio
async def test_delete_non_draft_raises(db: AsyncSession):
    """delete() on a non-draft SO raises ValidationError."""
    p = await _make_product(db, sku="SOU-DND")
    w = await _make_warehouse(db, code="SOU-DND")
    c = await _make_customer(db, code="SOU-DND")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    await _fast_transition(db, so, SalesOrderStatus.confirmed)

    svc = SalesOrderService(db)
    with pytest.raises(ValidationError, match="Only draft"):
        await svc.delete(so.id, TID)


@pytest.mark.asyncio
async def test_apply_discount_draft(db: AsyncSession):
    """apply_discount() updates totals on a draft SO."""
    p = await _make_product(db, sku="SOU-AD1")
    w = await _make_warehouse(db, code="SOU-AD1")
    c = await _make_customer(db, code="SOU-AD1")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=10, unit_price=10000)
    svc = SalesOrderService(db)
    result = await svc.apply_discount(so.id, TID, discount_pct=10.0, discount_reason="Loyalty")

    assert result.discount_pct == Decimal("10")
    assert result.discount_reason == "Loyalty"
    # Subtotal = 10 * 10000 = 100000, discount = 10000
    assert result.discount_amount == Decimal("10000.00")


@pytest.mark.asyncio
async def test_apply_discount_non_draft_raises(db: AsyncSession):
    """apply_discount() on a non-draft SO raises ValidationError."""
    p = await _make_product(db, sku="SOU-ADND")
    w = await _make_warehouse(db, code="SOU-ADND")
    c = await _make_customer(db, code="SOU-ADND")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    await _fast_transition(db, so, SalesOrderStatus.confirmed)

    svc = SalesOrderService(db)
    with pytest.raises(ValidationError, match="borrador"):
        await svc.apply_discount(so.id, TID, discount_pct=5.0)


@pytest.mark.asyncio
async def test_apply_discount_out_of_range(db: AsyncSession):
    """apply_discount() with pct > 100 or < 0 raises ValidationError."""
    p = await _make_product(db, sku="SOU-ADOR")
    w = await _make_warehouse(db, code="SOU-ADOR")
    c = await _make_customer(db, code="SOU-ADOR")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    svc = SalesOrderService(db)

    with pytest.raises(ValidationError, match="entre 0%"):
        await svc.apply_discount(so.id, TID, discount_pct=150.0)

    with pytest.raises(ValidationError, match="entre 0%"):
        await svc.apply_discount(so.id, TID, discount_pct=-5.0)


@pytest.mark.asyncio
async def test_update_line_warehouse_draft(db: AsyncSession):
    """update_line_warehouse() changes the warehouse on a draft line."""
    p = await _make_product(db, sku="SOU-ULW")
    w1 = await _make_warehouse(db, code="SOU-ULW1")
    w2 = await _make_warehouse(db, code="SOU-ULW2")
    c = await _make_customer(db, code="SOU-ULW")
    await _add_stock(db, p.id, w1.id)

    so = await _create_draft_so(db, c.id, w1.id, p.id)
    line_id = so.lines[0].id

    svc = SalesOrderService(db)
    updated = await svc.update_line_warehouse(so.id, line_id, w2.id, TID)
    updated_line = next(l for l in updated.lines if l.id == line_id)
    assert updated_line.warehouse_id == w2.id


@pytest.mark.asyncio
async def test_update_line_warehouse_wrong_status_raises(db: AsyncSession):
    """update_line_warehouse() on a shipped SO raises ValidationError."""
    p = await _make_product(db, sku="SOU-ULWS")
    w1 = await _make_warehouse(db, code="SOU-ULWS1")
    w2 = await _make_warehouse(db, code="SOU-ULWS2")
    c = await _make_customer(db, code="SOU-ULWS")
    await _add_stock(db, p.id, w1.id)

    so = await _create_draft_so(db, c.id, w1.id, p.id)
    await _fast_transition(db, so, SalesOrderStatus.shipped)

    svc = SalesOrderService(db)
    with pytest.raises(ValidationError, match="borrador o confirmadas"):
        await svc.update_line_warehouse(so.id, so.lines[0].id, w2.id, TID)


@pytest.mark.asyncio
async def test_update_line_warehouse_line_not_found(db: AsyncSession):
    """update_line_warehouse() with invalid line_id raises NotFoundError."""
    p = await _make_product(db, sku="SOU-ULNF")
    w = await _make_warehouse(db, code="SOU-ULNF")
    c = await _make_customer(db, code="SOU-ULNF")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    svc = SalesOrderService(db)
    with pytest.raises(NotFoundError, match="no encontrada"):
        await svc.update_line_warehouse(so.id, uid(), w.id, TID)


@pytest.mark.asyncio
async def test_update_line_warehouse_wh_not_found(db: AsyncSession):
    """update_line_warehouse() with invalid warehouse_id raises NotFoundError."""
    p = await _make_product(db, sku="SOU-ULWNF")
    w = await _make_warehouse(db, code="SOU-ULWNF")
    c = await _make_customer(db, code="SOU-ULWNF")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    svc = SalesOrderService(db)
    with pytest.raises(NotFoundError, match="Bodega no encontrada"):
        await svc.update_line_warehouse(so.id, so.lines[0].id, uid(), TID)


@pytest.mark.asyncio
async def test_stock_check_sufficient(db: AsyncSession):
    """stock_check() reports sufficient when stock >= required."""
    p = await _make_product(db, sku="SOU-SC1")
    w = await _make_warehouse(db, code="SOU-SC1")
    c = await _make_customer(db, code="SOU-SC1")
    await _add_stock(db, p.id, w.id, qty=Decimal("100"))

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=10)
    svc = SalesOrderService(db)
    result = await svc.stock_check(so.id, TID)
    assert result["ready_to_ship"] is True
    assert result["lines"][0]["sufficient"] is True


@pytest.mark.asyncio
async def test_stock_check_insufficient(db: AsyncSession):
    """stock_check() reports insufficient when stock < required."""
    p = await _make_product(db, sku="SOU-SCI")
    w = await _make_warehouse(db, code="SOU-SCI")
    c = await _make_customer(db, code="SOU-SCI")
    await _add_stock(db, p.id, w.id, qty=Decimal("5"))

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=20)
    svc = SalesOrderService(db)
    result = await svc.stock_check(so.id, TID)
    assert result["ready_to_ship"] is False
    assert result["lines"][0]["sufficient"] is False


@pytest.mark.asyncio
async def test_stock_check_no_warehouse(db: AsyncSession):
    """stock_check() marks line as insufficient when no warehouse assigned."""
    p = await _make_product(db, sku="SOU-SCNW")
    w = await _make_warehouse(db, code="SOU-SCNW")
    c = await _make_customer(db, code="SOU-SCNW")
    await _add_stock(db, p.id, w.id)

    # Create SO without warehouse_id
    svc = SalesOrderService(db)
    with patch("app.services.customer_price_service.CustomerPriceService.get_customer_price",
               new_callable=AsyncMock, return_value=None), \
         patch("app.services.tax_service.TaxService.get_product_tax_rate",
               new_callable=AsyncMock, return_value=(Decimal("0"), None)):
        so = await svc.create(
            TID,
            data={"customer_id": c.id},
            lines=[{"product_id": p.id, "qty_ordered": 5, "unit_price": 1000}],
            user_id="test-user",
        )

    result = await svc.stock_check(so.id, TID)
    assert result["ready_to_ship"] is False
    assert result["lines"][0]["warehouse_name"] == "Sin bodega"


@pytest.mark.asyncio
async def test_cancel_draft_so(db: AsyncSession):
    """cancel() transitions a draft SO to canceled."""
    p = await _make_product(db, sku="SOU-CD")
    w = await _make_warehouse(db, code="SOU-CD")
    c = await _make_customer(db, code="SOU-CD")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    svc = SalesOrderService(db)

    with patch("app.services.reservation_service.ReservationService") as MockRes:
        MockRes.return_value.release_for_so = AsyncMock()
        result = await svc.cancel(so.id, TID, user_id="test-user")

    assert result.status == SalesOrderStatus.canceled


@pytest.mark.asyncio
async def test_cancel_confirmed_releases_reservations(db: AsyncSession):
    """cancel() on a confirmed SO calls release_for_so."""
    p = await _make_product(db, sku="SOU-CCR")
    w = await _make_warehouse(db, code="SOU-CCR")
    c = await _make_customer(db, code="SOU-CCR")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    await _fast_transition(db, so, SalesOrderStatus.confirmed)

    svc = SalesOrderService(db)
    with patch("app.services.reservation_service.ReservationService") as MockRes:
        mock_release = AsyncMock()
        MockRes.return_value.release_for_so = mock_release
        result = await svc.cancel(so.id, TID, user_id="test-user")

    assert result.status == SalesOrderStatus.canceled
    mock_release.assert_called_once_with(so.id, TID, "canceled")


@pytest.mark.asyncio
async def test_cancel_returned_raises(db: AsyncSession):
    """cancel() on a returned (terminal) SO raises ValidationError."""
    p = await _make_product(db, sku="SOU-CRR")
    w = await _make_warehouse(db, code="SOU-CRR")
    c = await _make_customer(db, code="SOU-CRR")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    await _fast_transition(db, so, SalesOrderStatus.returned)

    svc = SalesOrderService(db)
    with pytest.raises(ValidationError, match="Cannot transition"):
        await svc.cancel(so.id, TID)


@pytest.mark.asyncio
async def test_start_picking_confirmed(db: AsyncSession):
    """start_picking() transitions confirmed → picking when stock is sufficient."""
    p = await _make_product(db, sku="SOU-SP1")
    w = await _make_warehouse(db, code="SOU-SP1")
    c = await _make_customer(db, code="SOU-SP1")
    await _add_stock(db, p.id, w.id, qty=Decimal("100"))

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=10)
    await _fast_transition(db, so, SalesOrderStatus.confirmed)

    svc = SalesOrderService(db)
    result = await svc.start_picking(so.id, TID, user_id="picker")
    assert result.status == SalesOrderStatus.picking


@pytest.mark.asyncio
async def test_start_picking_insufficient_stock_raises(db: AsyncSession):
    """start_picking() raises when stock is insufficient."""
    p = await _make_product(db, sku="SOU-SPIS")
    w = await _make_warehouse(db, code="SOU-SPIS")
    c = await _make_customer(db, code="SOU-SPIS")
    await _add_stock(db, p.id, w.id, qty=Decimal("2"))

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=50)
    await _fast_transition(db, so, SalesOrderStatus.confirmed)

    svc = SalesOrderService(db)
    with pytest.raises(ValidationError, match="Stock insuficiente"):
        await svc.start_picking(so.id, TID)


@pytest.mark.asyncio
async def test_start_picking_from_draft_raises(db: AsyncSession):
    """start_picking() from draft raises (invalid transition)."""
    p = await _make_product(db, sku="SOU-SPD")
    w = await _make_warehouse(db, code="SOU-SPD")
    c = await _make_customer(db, code="SOU-SPD")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    svc = SalesOrderService(db)
    with pytest.raises(ValidationError, match="Cannot transition"):
        await svc.start_picking(so.id, TID)


@pytest.mark.asyncio
async def test_ship_picking_order(db: AsyncSession):
    """ship() transitions picking → shipped, sets qty_shipped and remission_number."""
    p = await _make_product(db, sku="SOU-SH1")
    w = await _make_warehouse(db, code="SOU-SH1")
    c = await _make_customer(db, code="SOU-SH1")
    await _add_stock(db, p.id, w.id, qty=Decimal("100"))

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=10)
    await _fast_transition(db, so, SalesOrderStatus.picking)

    svc = SalesOrderService(db)
    result = await svc.ship(so.id, TID, user_id="shipper")
    assert result.status == SalesOrderStatus.shipped
    assert result.remission_number is not None
    assert result.remission_number.startswith("REM-")
    assert result.lines[0].qty_shipped == Decimal("10")


@pytest.mark.asyncio
async def test_ship_with_shipping_info(db: AsyncSession):
    """ship() persists shipping_info into extra_data."""
    p = await _make_product(db, sku="SOU-SSI")
    w = await _make_warehouse(db, code="SOU-SSI")
    c = await _make_customer(db, code="SOU-SSI")
    await _add_stock(db, p.id, w.id, qty=Decimal("100"))

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=5)
    await _fast_transition(db, so, SalesOrderStatus.picking)

    svc = SalesOrderService(db)
    result = await svc.ship(
        so.id, TID,
        shipping_info={"carrier": "FedEx", "tracking_number": "FX123", "city": "Bogota"},
        user_id="shipper",
    )
    assert result.extra_data.get("shipping_info", {}).get("carrier") == "FedEx"
    assert result.shipping_address.get("city") == "Bogota"


@pytest.mark.asyncio
async def test_ship_no_warehouse_raises(db: AsyncSession):
    """ship() raises when a line has no effective warehouse."""
    p = await _make_product(db, sku="SOU-SNW")
    c = await _make_customer(db, code="SOU-SNW")

    svc = SalesOrderService(db)
    with patch("app.services.customer_price_service.CustomerPriceService.get_customer_price",
               new_callable=AsyncMock, return_value=None), \
         patch("app.services.tax_service.TaxService.get_product_tax_rate",
               new_callable=AsyncMock, return_value=(Decimal("0"), None)):
        so = await svc.create(
            TID,
            data={"customer_id": c.id},
            lines=[{"product_id": p.id, "qty_ordered": 5, "unit_price": 1000}],
            user_id="test-user",
        )
    await _fast_transition(db, so, SalesOrderStatus.picking)

    with pytest.raises(ValidationError, match="no tiene bodega"):
        await svc.ship(so.id, TID)


@pytest.mark.asyncio
async def test_deliver_shipped_order(db: AsyncSession):
    """deliver() transitions shipped → delivered, deducts stock."""
    p = await _make_product(db, sku="SOU-DL1")
    w = await _make_warehouse(db, code="SOU-DL1")
    c = await _make_customer(db, code="SOU-DL1")
    await _add_stock(db, p.id, w.id, qty=Decimal("100"))

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=10)
    # Set qty_shipped on line
    so.lines[0].qty_shipped = Decimal("10")
    await _fast_transition(db, so, SalesOrderStatus.shipped)

    svc = SalesOrderService(db)
    with patch("app.services.reservation_service.ReservationService") as MockRes:
        MockRes.return_value.consume_for_so = AsyncMock(return_value=True)
        with patch.object(svc.stock_service, "issue", new_callable=AsyncMock) as mock_issue:
            mock_issue.return_value = None
            result = await svc.deliver(so.id, TID, user_id="deliver-user")

    assert result.status == SalesOrderStatus.delivered


@pytest.mark.asyncio
async def test_return_delivered_order(db: AsyncSession):
    """return_order() transitions delivered → returned and restocks."""
    p = await _make_product(db, sku="SOU-RO1")
    w = await _make_warehouse(db, code="SOU-RO1")
    c = await _make_customer(db, code="SOU-RO1")
    await _add_stock(db, p.id, w.id, qty=Decimal("90"))

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=10)
    so.lines[0].qty_shipped = Decimal("10")
    await _fast_transition(db, so, SalesOrderStatus.delivered)

    svc = SalesOrderService(db)
    with patch("app.services.reservation_service.ReservationService") as MockRes:
        MockRes.return_value.release_for_so = AsyncMock()
        result = await svc.return_order(so.id, TID, user_id="return-user")

    assert result.status == SalesOrderStatus.returned
    assert result.returned_at is not None


@pytest.mark.asyncio
async def test_return_non_delivered_raises(db: AsyncSession):
    """return_order() from draft raises (invalid transition)."""
    p = await _make_product(db, sku="SOU-RND")
    w = await _make_warehouse(db, code="SOU-RND")
    c = await _make_customer(db, code="SOU-RND")
    await _add_stock(db, p.id, w.id)

    so = await _create_draft_so(db, c.id, w.id, p.id)
    svc = SalesOrderService(db)
    with pytest.raises(ValidationError, match="Cannot transition"):
        await svc.return_order(so.id, TID)


# ── State machine / _assert_transition ───────────────────────────────────────


@pytest.mark.asyncio
async def test_assert_transition_valid(db: AsyncSession):
    """_assert_transition allows valid transitions silently."""
    svc = SalesOrderService(db)

    class FakeOrder:
        status = SalesOrderStatus.draft

    # Should not raise
    svc._assert_transition(FakeOrder(), SalesOrderStatus.confirmed)
    svc._assert_transition(FakeOrder(), SalesOrderStatus.canceled)


@pytest.mark.asyncio
async def test_assert_transition_invalid(db: AsyncSession):
    """_assert_transition raises on invalid transition."""
    svc = SalesOrderService(db)

    class FakeOrder:
        status = SalesOrderStatus.canceled

    with pytest.raises(ValidationError, match="Cannot transition"):
        svc._assert_transition(FakeOrder(), SalesOrderStatus.confirmed)


@pytest.mark.asyncio
async def test_assert_transition_terminal_states(db: AsyncSession):
    """Terminal states (returned, canceled) allow no transitions."""
    svc = SalesOrderService(db)

    for terminal in (SalesOrderStatus.returned, SalesOrderStatus.canceled):
        class FakeOrder:
            status = terminal

        for target in SalesOrderStatus:
            if target == terminal:
                continue
            with pytest.raises(ValidationError):
                svc._assert_transition(FakeOrder(), target)


# ── recalculate_so_totals ────────────────────────────────────────────────────


def test_recalculate_so_totals_basic():
    """recalculate_so_totals computes correct values for simple case."""

    class FakeLine:
        qty_ordered = Decimal("10")
        unit_price = Decimal("1000")
        discount_pct = Decimal("0")
        tax_rate = Decimal("19")
        tax_rate_pct = None
        retention_pct = None
        discount_amount = Decimal("0")
        line_subtotal = Decimal("0")
        line_total = Decimal("0")
        tax_amount = Decimal("0")
        retention_amount = Decimal("0")
        line_total_with_tax = Decimal("0")

    class FakeSO:
        discount_pct = Decimal("0")
        lines = [FakeLine()]
        subtotal = Decimal("0")
        discount_amount = Decimal("0")
        tax_amount = Decimal("0")
        total = Decimal("0")
        total_retention = Decimal("0")
        total_with_tax = Decimal("0")
        total_payable = Decimal("0")

    so = FakeSO()
    recalculate_so_totals(so)

    # 10 * 1000 = 10000 subtotal, 19% tax = 1900
    assert so.subtotal == Decimal("10000.00")
    assert so.tax_amount == Decimal("1900.00")
    assert so.total == Decimal("11900.00")
    assert so.discount_amount == Decimal("0.00")


def test_recalculate_so_totals_with_discount():
    """recalculate_so_totals applies SO-level discount correctly."""

    class FakeLine:
        qty_ordered = Decimal("5")
        unit_price = Decimal("2000")
        discount_pct = Decimal("0")
        tax_rate = Decimal("19")
        tax_rate_pct = None
        retention_pct = None
        discount_amount = Decimal("0")
        line_subtotal = Decimal("0")
        line_total = Decimal("0")
        tax_amount = Decimal("0")
        retention_amount = Decimal("0")
        line_total_with_tax = Decimal("0")

    class FakeSO:
        discount_pct = Decimal("10")
        lines = [FakeLine()]
        subtotal = Decimal("0")
        discount_amount = Decimal("0")
        tax_amount = Decimal("0")
        total = Decimal("0")
        total_retention = Decimal("0")
        total_with_tax = Decimal("0")
        total_payable = Decimal("0")

    so = FakeSO()
    recalculate_so_totals(so)

    # subtotal = 5*2000 = 10000
    # discount = 10000 * 10% = 1000
    # tax = 10000 * 0.90 * 19% = 1710
    # total = 10000 - 1000 + 1710 = 10710
    assert so.subtotal == Decimal("10000.00")
    assert so.discount_amount == Decimal("1000.00")
    assert so.tax_amount == Decimal("1710.00")
    assert so.total == Decimal("10710.00")


def test_recalculate_so_totals_with_line_discount():
    """recalculate_so_totals applies per-line discount correctly."""

    class FakeLine:
        qty_ordered = Decimal("10")
        unit_price = Decimal("1000")
        discount_pct = Decimal("20")  # 20% line discount
        tax_rate = Decimal("0")
        tax_rate_pct = None
        retention_pct = None
        discount_amount = Decimal("0")
        line_subtotal = Decimal("0")
        line_total = Decimal("0")
        tax_amount = Decimal("0")
        retention_amount = Decimal("0")
        line_total_with_tax = Decimal("0")

    class FakeSO:
        discount_pct = Decimal("0")
        lines = [FakeLine()]
        subtotal = Decimal("0")
        discount_amount = Decimal("0")
        tax_amount = Decimal("0")
        total = Decimal("0")
        total_retention = Decimal("0")
        total_with_tax = Decimal("0")
        total_payable = Decimal("0")

    so = FakeSO()
    recalculate_so_totals(so)

    # base = 10*1000 = 10000, line discount = 20% of 10000 = 2000
    # line_subtotal = 10000 - 2000 = 8000
    assert so.lines[0].line_subtotal == Decimal("8000.0000")
    assert so.subtotal == Decimal("8000.00")
    assert so.total == Decimal("8000.00")


def test_recalculate_so_totals_retention():
    """recalculate_so_totals handles retention_pct."""

    class FakeLine:
        qty_ordered = Decimal("1")
        unit_price = Decimal("100000")
        discount_pct = Decimal("0")
        tax_rate = Decimal("19")
        tax_rate_pct = Decimal("0.19")
        retention_pct = Decimal("0.025")  # 2.5% retention
        discount_amount = Decimal("0")
        line_subtotal = Decimal("0")
        line_total = Decimal("0")
        tax_amount = Decimal("0")
        retention_amount = Decimal("0")
        line_total_with_tax = Decimal("0")

    class FakeSO:
        discount_pct = Decimal("0")
        lines = [FakeLine()]
        subtotal = Decimal("0")
        discount_amount = Decimal("0")
        tax_amount = Decimal("0")
        total = Decimal("0")
        total_retention = Decimal("0")
        total_with_tax = Decimal("0")
        total_payable = Decimal("0")

    so = FakeSO()
    recalculate_so_totals(so)

    # retention = 100000 * 0.025 = 2500
    assert so.total_retention == Decimal("2500.00")
    assert so.total_payable == so.total_with_tax - so.total_retention


# ── VALID_TRANSITIONS map ───────────────────────────────────────────────────


def test_valid_transitions_completeness():
    """Every SalesOrderStatus value exists as a key in VALID_TRANSITIONS."""
    for status in SalesOrderStatus:
        assert status in VALID_TRANSITIONS, f"{status} missing from VALID_TRANSITIONS"


def test_valid_transitions_terminal_empty():
    """Terminal states have no allowed transitions."""
    assert VALID_TRANSITIONS[SalesOrderStatus.returned] == []
    assert VALID_TRANSITIONS[SalesOrderStatus.canceled] == []


# ── Confirm flow (with mocking) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_draft_order(db: AsyncSession):
    """confirm() transitions draft → confirmed when stock available."""
    p = await _make_product(db, sku="SOU-CF1")
    w = await _make_warehouse(db, code="SOU-CF1")
    c = await _make_customer(db, code="SOU-CF1")
    await _add_stock(db, p.id, w.id, qty=Decimal("100"))

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=10)
    svc = SalesOrderService(db)

    with patch("app.services.approval_service.ApprovalService") as MockAppr, \
         patch("app.services.backorder_service.BackorderService") as MockBO, \
         patch("app.services.reservation_service.ReservationService") as MockRes:
        MockAppr.return_value.requires_approval = AsyncMock(return_value=False)
        MockBO.return_value.analyze_and_split = AsyncMock(return_value={
            "needs_backorder": False,
            "confirmable_lines": [(so.lines[0].id, Decimal("10"))],
            "backorder_lines": [],
            "preview": [],
        })
        MockRes.return_value.reserve_for_so = AsyncMock()
        with patch.object(svc, "_check_reorder_for_lines", new_callable=AsyncMock):
            with patch.object(svc, "_try_einvoice", new_callable=AsyncMock):
                result = await svc.confirm(so.id, TID, user_id="confirmer")

    assert result["order"].status == SalesOrderStatus.confirmed
    assert result["approval_required"] is False
    assert result["backorder"] is None


@pytest.mark.asyncio
async def test_confirm_requires_approval(db: AsyncSession):
    """confirm() routes to pending_approval when threshold exceeded."""
    p = await _make_product(db, sku="SOU-CFA")
    w = await _make_warehouse(db, code="SOU-CFA")
    c = await _make_customer(db, code="SOU-CFA")
    await _add_stock(db, p.id, w.id, qty=Decimal("100"))

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=10, unit_price=100000)
    svc = SalesOrderService(db)

    with patch("app.services.approval_service.ApprovalService") as MockAppr:
        MockAppr.return_value.requires_approval = AsyncMock(return_value=True)
        MockAppr.return_value.request_approval = AsyncMock()
        result = await svc.confirm(so.id, TID, user_id="u1", user_name="User 1")

    assert result["approval_required"] is True
    assert result["backorder"] is None


@pytest.mark.asyncio
async def test_confirm_no_stock_raises(db: AsyncSession):
    """confirm() raises when no stock available for any line."""
    p = await _make_product(db, sku="SOU-CFNS")
    w = await _make_warehouse(db, code="SOU-CFNS")
    c = await _make_customer(db, code="SOU-CFNS")
    # No stock added

    so = await _create_draft_so(db, c.id, w.id, p.id, qty=10)
    svc = SalesOrderService(db)

    with patch("app.services.approval_service.ApprovalService") as MockAppr, \
         patch("app.services.backorder_service.BackorderService") as MockBO:
        MockAppr.return_value.requires_approval = AsyncMock(return_value=False)
        MockBO.return_value.analyze_and_split = AsyncMock(return_value={
            "needs_backorder": False,
            "confirmable_lines": [],
            "backorder_lines": [],
            "preview": [],
        })
        with pytest.raises(ValidationError, match="no hay stock"):
            await svc.confirm(so.id, TID)
