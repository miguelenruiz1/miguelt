"""Tests for refund / credit note issuance (FASE2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db.models import Invoice, InvoiceStatus
from app.services.invoice_service import issue_credit_note


async def _ensure_counter_table(db):
    # The sequence_counters table is created by migration 011; in tests we use
    # Base.metadata.create_all — ensure the table exists on SQLite.
    await db.execute(
        text(
            "CREATE TABLE IF NOT EXISTS sequence_counters ("
            "scope TEXT PRIMARY KEY, value INTEGER NOT NULL, updated_at TEXT)"
        )
    )


@pytest.mark.asyncio
async def test_full_refund_creates_credit_note_and_voids_parent(
    db, make_plan, make_subscription, monkeypatch
):
    await _ensure_counter_table(db)

    # Disable email side-effect
    async def noop(*a, **kw):
        return None
    monkeypatch.setattr(
        "app.services.invoice_service._fetch_tenant_owner",
        lambda tid: noop(tid),
    )

    plan = await make_plan(slug="p-ref", price_monthly=Decimal("100000"))
    sub = await make_subscription(plan, tenant_id="t-ref")
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-ref-1",
        subscription_id=sub.id,
        tenant_id="t-ref",
        invoice_number="INV-2026-0900",
        status=InvoiceStatus.paid,
        amount=Decimal("100000"),
        currency="COP",
        period_start=now,
        period_end=now + timedelta(days=30),
        paid_at=now,
        line_items=[],
        invoice_type="standard",
    )
    db.add(inv)
    await db.flush()

    result = await issue_credit_note(
        db=db,
        tenant_id="t-ref",
        invoice_id="inv-ref-1",
        reason="Customer request",
        partial_amount=None,
        performed_by="admin",
    )
    assert result["full_refund"] is True
    assert result["credit_note_number"].startswith("NC-")
    assert result["amount"] == 100000.0

    # Parent should be void
    await db.refresh(inv)
    assert inv.status == InvoiceStatus.void

    # Credit note row exists with negative amount
    from sqlalchemy import select
    res = await db.execute(select(Invoice).where(Invoice.id == result["credit_note_id"]))
    cn = res.scalar_one()
    assert cn.invoice_type == "credit_note"
    assert cn.amount == Decimal("-100000")
    assert cn.parent_invoice_id == "inv-ref-1"


@pytest.mark.asyncio
async def test_partial_refund_leaves_parent_paid(
    db, make_plan, make_subscription, monkeypatch
):
    await _ensure_counter_table(db)

    async def noop(*a, **kw):
        return None
    monkeypatch.setattr(
        "app.services.invoice_service._fetch_tenant_owner",
        lambda tid: noop(tid),
    )

    plan = await make_plan(slug="p-ref2", price_monthly=Decimal("100000"))
    sub = await make_subscription(plan, tenant_id="t-ref2")
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-ref-2",
        subscription_id=sub.id,
        tenant_id="t-ref2",
        invoice_number="INV-2026-0901",
        status=InvoiceStatus.paid,
        amount=Decimal("100000"),
        currency="COP",
        period_start=now,
        period_end=now + timedelta(days=30),
        paid_at=now,
        line_items=[],
        invoice_type="standard",
    )
    db.add(inv)
    await db.flush()

    result = await issue_credit_note(
        db=db,
        tenant_id="t-ref2",
        invoice_id="inv-ref-2",
        reason="Partial",
        partial_amount=30000.0,
        performed_by="admin",
    )
    assert result["full_refund"] is False
    assert result["amount"] == 30000.0

    await db.refresh(inv)
    assert inv.status == InvoiceStatus.paid  # not voided


@pytest.mark.asyncio
async def test_refund_rejects_refunding_a_credit_note(
    db, make_plan, make_subscription
):
    await _ensure_counter_table(db)
    plan = await make_plan(slug="p-ref3", price_monthly=Decimal("1000"))
    sub = await make_subscription(plan, tenant_id="t-ref3")
    now = datetime.now(timezone.utc)
    inv = Invoice(
        id="inv-ref-3",
        subscription_id=sub.id,
        tenant_id="t-ref3",
        invoice_number="NC-2026-0001",
        status=InvoiceStatus.paid,
        amount=Decimal("-1000"),
        currency="COP",
        period_start=now,
        period_end=now + timedelta(days=30),
        line_items=[],
        invoice_type="credit_note",
    )
    db.add(inv)
    await db.flush()

    with pytest.raises(ValueError, match="credit note"):
        await issue_credit_note(
            db=db, tenant_id="t-ref3", invoice_id="inv-ref-3",
            reason="x", partial_amount=None, performed_by="admin",
        )
