"""Tests for invoice PDF rendering (FASE2)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.db.models import Invoice, InvoiceStatus
from app.services.invoice_pdf_service import (
    _fmt_money,
    build_invoice_context,
    render_invoice_html,
    render_invoice_pdf,
)


def test_fmt_money_colombian_style():
    assert _fmt_money(Decimal("49000.00"), "COP") == "$49.000,00"
    assert _fmt_money(Decimal("1234567.50"), "COP") == "$1.234.567,50"
    assert _fmt_money(Decimal("-100.25"), "COP") == "-$100,25"


@pytest.mark.asyncio
async def test_build_context_computes_iva(db, make_plan, make_subscription):
    plan = await make_plan(slug="starter-pdf", price_monthly=Decimal("119000"))
    sub = await make_subscription(plan, tenant_id="t-pdf-1")
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-pdf-1",
        subscription_id=sub.id,
        tenant_id="t-pdf-1",
        invoice_number="INV-2026-0001",
        status=InvoiceStatus.open,
        amount=Decimal("119000.00"),
        currency="COP",
        period_start=now,
        period_end=now + timedelta(days=30),
        due_date=date.today() + timedelta(days=15),
        line_items=[{"description": "Starter plan — monthly", "quantity": 1, "unit_price": 119000.0, "amount": 119000.0}],
        invoice_type="standard",
    )
    db.add(inv)
    await db.flush()

    ctx = await build_invoice_context(db, inv)
    assert ctx.invoice["invoice_number"] == "INV-2026-0001"
    assert "100.000" in ctx.totals["subtotal_fmt"]  # 119000 / 1.19 = 100000
    assert "19.000" in ctx.totals["iva_fmt"]
    assert ctx.line_items
    assert ctx.customer["name"].startswith("Tenant ")


@pytest.mark.asyncio
async def test_render_invoice_html_contains_key_fields(db, make_plan, make_subscription):
    plan = await make_plan(slug="starter-pdf2", price_monthly=Decimal("49000"))
    sub = await make_subscription(plan, tenant_id="t-pdf-2")
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-pdf-2",
        subscription_id=sub.id,
        tenant_id="t-pdf-2",
        invoice_number="INV-2026-0099",
        status=InvoiceStatus.open,
        amount=Decimal("49000.00"),
        currency="COP",
        period_start=now,
        period_end=now + timedelta(days=30),
        line_items=[],
        invoice_type="standard",
    )
    db.add(inv)
    await db.flush()

    ctx = await build_invoice_context(db, inv)
    html = render_invoice_html(ctx)
    assert "INV-2026-0099" in html
    assert "TRACE" in html
    assert "IVA" in html
    assert "Bancolombia" in html  # footer bank info
    assert len(html) > 2000


@pytest.mark.asyncio
async def test_render_pdf_produces_bytes(db, make_plan, make_subscription):
    """Smoke test — skipped automatically if weasyprint not installed."""
    pytest.importorskip("weasyprint")

    plan = await make_plan(slug="starter-pdf3", price_monthly=Decimal("49000"))
    sub = await make_subscription(plan, tenant_id="t-pdf-3")
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-pdf-3",
        subscription_id=sub.id,
        tenant_id="t-pdf-3",
        invoice_number="INV-2026-0500",
        status=InvoiceStatus.open,
        amount=Decimal("49000.00"),
        currency="COP",
        period_start=now,
        period_end=now + timedelta(days=30),
        line_items=[],
        invoice_type="standard",
    )
    db.add(inv)
    await db.flush()

    pdf_bytes = await render_invoice_pdf(db, "inv-pdf-3")
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 1000
    assert pdf_bytes[:4] == b"%PDF"
