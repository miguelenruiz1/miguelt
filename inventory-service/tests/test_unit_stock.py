"""Unit tests — call StockService methods directly to cover internal branches."""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Product, Warehouse, StockLevel
from app.db.models.enums import WarehouseType, MovementType
from app.db.models.warehouse import WarehouseLocation
from app.services.stock_service import StockService


TENANT = "test-tenant"


async def _receive_and_approve(svc: StockService, db: AsyncSession, pid: str, wid: str,
                                qty: Decimal, cost: Decimal, **kw):
    """Receive stock and approve QC so it can be issued/transferred."""
    mov = await svc.receive(TENANT, pid, wid, qty, unit_cost=cost, **kw)
    await svc.qc_approve(TENANT, pid, wid)
    return mov


async def _mk_product(db: AsyncSession, sku: str, **kw) -> Product:
    p = Product(id=str(uuid.uuid4()), tenant_id=TENANT, sku=sku, name=f"P-{sku}",
                unit_of_measure="un", is_active=True, **kw)
    db.add(p)
    await db.flush()
    return p


async def _mk_warehouse(db: AsyncSession, code: str, **kw) -> Warehouse:
    w = Warehouse(id=str(uuid.uuid4()), tenant_id=TENANT, name=f"WH-{code}",
                  code=code, type=WarehouseType.main, is_active=True, **kw)
    db.add(w)
    await db.flush()
    return w


async def _mk_location(db: AsyncSession, wh_id: str, code: str, **kw) -> WarehouseLocation:
    defaults = {"blocked_inbound": False, "blocked_outbound": False}
    defaults.update(kw)
    loc = WarehouseLocation(id=str(uuid.uuid4()), tenant_id=TENANT,
                            warehouse_id=wh_id, name=code, code=code, is_active=True, **defaults)
    db.add(loc)
    await db.flush()
    return loc


# ── Receive ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_receive_basic(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-001")
    w = await _mk_warehouse(db, "USRV-W1")

    mov = await svc.receive(TENANT, p.id, w.id, Decimal("100"), unit_cost=Decimal("5000"),
                            reference="PO-1", performed_by="tester")
    assert mov.movement_type == MovementType.purchase
    assert mov.quantity == Decimal("100")


@pytest.mark.asyncio
async def test_svc_receive_zero_qty_fails(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-002")
    w = await _mk_warehouse(db, "USRV-W2")

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError):
        await svc.receive(TENANT, p.id, w.id, Decimal("0"), unit_cost=Decimal("100"))


@pytest.mark.asyncio
async def test_svc_receive_no_cost_fails(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-003")
    w = await _mk_warehouse(db, "USRV-W3")

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError):
        await svc.receive(TENANT, p.id, w.id, Decimal("10"), unit_cost=None)


@pytest.mark.asyncio
async def test_svc_receive_with_location(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-004")
    w = await _mk_warehouse(db, "USRV-W4")
    loc = await _mk_location(db, w.id, "LOC-A")

    mov = await svc.receive(TENANT, p.id, w.id, Decimal("50"), unit_cost=Decimal("3000"),
                            location_id=loc.id)
    assert mov is not None


@pytest.mark.asyncio
async def test_svc_receive_blocked_location(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-005")
    w = await _mk_warehouse(db, "USRV-W5")
    loc = await _mk_location(db, w.id, "LOC-BLK", blocked_inbound=True, block_reason="Maint")

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError, match="bloqueada"):
        await svc.receive(TENANT, p.id, w.id, Decimal("10"), unit_cost=Decimal("1000"),
                          location_id=loc.id)


@pytest.mark.asyncio
async def test_svc_receive_max_capacity(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-006")
    w = await _mk_warehouse(db, "USRV-W6")
    loc = await _mk_location(db, w.id, "LOC-SM", max_capacity=5)

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError, match="[Cc]apacidad"):
        await svc.receive(TENANT, p.id, w.id, Decimal("10"), unit_cost=Decimal("1000"),
                          location_id=loc.id)


@pytest.mark.asyncio
async def test_svc_receive_max_weight(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-007", weight_per_unit=Decimal("5.0"))
    w = await _mk_warehouse(db, "USRV-W7")
    loc = await _mk_location(db, w.id, "LOC-WT", max_weight_kg=20.0)

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError, match="[Pp]eso"):
        await svc.receive(TENANT, p.id, w.id, Decimal("10"), unit_cost=Decimal("1000"),
                          location_id=loc.id)  # 10*5=50kg > 20kg


# ── Issue ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_issue_basic(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-I01")
    w = await _mk_warehouse(db, "USRV-WI1")
    await _receive_and_approve(svc, db, p.id, w.id, Decimal("100"), Decimal("5000"))

    mov = await svc.issue(TENANT, p.id, w.id, Decimal("30"), reference="SO-1")
    assert mov.movement_type == MovementType.sale
    assert mov.quantity == Decimal("30")


@pytest.mark.asyncio
async def test_svc_issue_insufficient(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-I02")
    w = await _mk_warehouse(db, "USRV-WI2")
    await _receive_and_approve(svc, db, p.id, w.id, Decimal("5"), Decimal("1000"))

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError, match="[Ii]nsufficient"):
        await svc.issue(TENANT, p.id, w.id, Decimal("50"))


@pytest.mark.asyncio
async def test_svc_issue_qc_blocked(db: AsyncSession):
    """Stock in pending_qc should be blocked from issuing."""
    svc = StockService(db)
    p = await _mk_product(db, "USRV-I03")
    w = await _mk_warehouse(db, "USRV-WI3")
    await svc.receive(TENANT, p.id, w.id, Decimal("100"), unit_cost=Decimal("5000"))

    # Manually set QC status
    from sqlalchemy import select, update
    await db.execute(
        update(StockLevel)
        .where(StockLevel.product_id == p.id, StockLevel.warehouse_id == w.id)
        .values(qc_status="pending_qc")
    )
    await db.flush()

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError, match="[Cc]uarentena"):
        await svc.issue(TENANT, p.id, w.id, Decimal("10"))


# ── Transfer ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_transfer(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-T01")
    w1 = await _mk_warehouse(db, "USRV-WT1")
    w2 = await _mk_warehouse(db, "USRV-WT2")
    await _receive_and_approve(svc, db, p.id, w1.id, Decimal("100"), Decimal("5000"))

    mov = await svc.transfer(TENANT, p.id, w1.id, w2.id, Decimal("40"))
    assert mov.movement_type == MovementType.transfer


@pytest.mark.asyncio
async def test_svc_transfer_same_warehouse_fails(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-T02")
    w = await _mk_warehouse(db, "USRV-WT3")
    await _receive_and_approve(svc, db, p.id, w.id, Decimal("100"), Decimal("5000"))

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError, match="[Dd]iffer"):
        await svc.transfer(TENANT, p.id, w.id, w.id, Decimal("10"))


@pytest.mark.asyncio
async def test_svc_transfer_insufficient(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-T03")
    w1 = await _mk_warehouse(db, "USRV-WT4")
    w2 = await _mk_warehouse(db, "USRV-WT5")
    await _receive_and_approve(svc, db, p.id, w1.id, Decimal("5"), Decimal("1000"))

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError):
        await svc.transfer(TENANT, p.id, w1.id, w2.id, Decimal("50"))


# ── Two-phase transfer ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_initiate_and_complete_transfer(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-2P1")
    w1 = await _mk_warehouse(db, "USRV-W2P1")
    w2 = await _mk_warehouse(db, "USRV-W2P2")
    await _receive_and_approve(svc, db, p.id, w1.id, Decimal("100"), Decimal("5000"))

    mov = await svc.initiate_transfer(TENANT, p.id, w1.id, w2.id, Decimal("30"))
    assert mov.status == "in_transit"

    completed = await svc.complete_transfer(TENANT, mov.id)
    assert completed.status == "completed"


# ── Adjust ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_adjust_down(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-AD1")
    w = await _mk_warehouse(db, "USRV-WAD1")
    await svc.receive(TENANT, p.id, w.id, Decimal("100"), unit_cost=Decimal("5000"))

    mov = await svc.adjust(TENANT, p.id, w.id, Decimal("90"), reason="Count")
    assert mov.movement_type == MovementType.adjustment_out


@pytest.mark.asyncio
async def test_svc_adjust_up(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-AU1")
    w = await _mk_warehouse(db, "USRV-WAU1")
    await svc.receive(TENANT, p.id, w.id, Decimal("50"), unit_cost=Decimal("3000"))

    mov = await svc.adjust(TENANT, p.id, w.id, Decimal("60"), reason="Found")
    assert mov.movement_type == MovementType.adjustment_in


# ── Adjust in / out ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_adjust_in(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-AIN")
    w = await _mk_warehouse(db, "USRV-WAIN")

    mov = await svc.adjust_in(TENANT, p.id, w.id, Decimal("25"), reason="Found",
                              unit_cost=Decimal("2000"))
    assert mov.movement_type == MovementType.adjustment_in


@pytest.mark.asyncio
async def test_svc_adjust_out(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-AOUT")
    w = await _mk_warehouse(db, "USRV-WAOUT")
    await _receive_and_approve(svc, db, p.id, w.id, Decimal("100"), Decimal("5000"))

    mov = await svc.adjust_out(TENANT, p.id, w.id, Decimal("10"), reason="Cycle count")
    assert mov.movement_type == MovementType.adjustment_out


@pytest.mark.asyncio
async def test_svc_adjust_out_insufficient(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-AOI")
    w = await _mk_warehouse(db, "USRV-WAOI")
    await _receive_and_approve(svc, db, p.id, w.id, Decimal("5"), Decimal("1000"))

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError):
        await svc.adjust_out(TENANT, p.id, w.id, Decimal("50"), reason="Oops")


# ── Return ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_return_with_cost(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-RET1")
    w = await _mk_warehouse(db, "USRV-WRET1")
    await svc.receive(TENANT, p.id, w.id, Decimal("50"), unit_cost=Decimal("4000"))

    mov = await svc.return_stock(TENANT, p.id, w.id, Decimal("5"),
                                 unit_cost=Decimal("3500"), reference="RMA-1")
    assert mov.movement_type == MovementType.return_


@pytest.mark.asyncio
async def test_svc_return_without_cost(db: AsyncSession):
    """Return without explicit cost uses weighted_avg_cost."""
    svc = StockService(db)
    p = await _mk_product(db, "USRV-RET2")
    w = await _mk_warehouse(db, "USRV-WRET2")
    await svc.receive(TENANT, p.id, w.id, Decimal("50"), unit_cost=Decimal("4000"))

    mov = await svc.return_stock(TENANT, p.id, w.id, Decimal("5"))
    assert mov.movement_type == MovementType.return_


# ── Waste ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_waste(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-WST")
    w = await _mk_warehouse(db, "USRV-WWST")
    await _receive_and_approve(svc, db, p.id, w.id, Decimal("50"), Decimal("2000"))

    mov = await svc.waste(TENANT, p.id, w.id, Decimal("5"), reason="Damage")
    assert mov.movement_type == MovementType.waste


@pytest.mark.asyncio
async def test_svc_waste_insufficient(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-WSI")
    w = await _mk_warehouse(db, "USRV-WWSI")
    await _receive_and_approve(svc, db, p.id, w.id, Decimal("3"), Decimal("1000"))

    from app.core.errors import ValidationError
    with pytest.raises(ValidationError):
        await svc.waste(TENANT, p.id, w.id, Decimal("50"), reason="Oops")


# ── QC approve / reject ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_qc_approve(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-QCA")
    w = await _mk_warehouse(db, "USRV-WQCA")
    await svc.receive(TENANT, p.id, w.id, Decimal("50"), unit_cost=Decimal("3000"))

    level = await svc.qc_approve(TENANT, p.id, w.id)
    assert level.qc_status == "approved"


@pytest.mark.asyncio
async def test_svc_qc_reject(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-QCR")
    w = await _mk_warehouse(db, "USRV-WQCR")
    await svc.receive(TENANT, p.id, w.id, Decimal("50"), unit_cost=Decimal("3000"))

    level = await svc.qc_reject(TENANT, p.id, w.id, notes="Failed")
    assert level.qc_status == "rejected"


# ── Get summary ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_get_summary(db: AsyncSession):
    svc = StockService(db)
    p = await _mk_product(db, "USRV-SUM", min_stock_level=10, reorder_point=5)
    w = await _mk_warehouse(db, "USRV-WSUM")
    await svc.receive(TENANT, p.id, w.id, Decimal("100"), unit_cost=Decimal("5000"))

    summary = await svc.get_summary(TENANT)
    assert "total_skus" in summary
    assert "total_value" in summary
    assert "low_stock_count" in summary
    assert "out_of_stock_count" in summary
    assert summary["total_skus"] >= 1
