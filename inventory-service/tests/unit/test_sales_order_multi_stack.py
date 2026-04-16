"""Regression: recalculate_so_totals does not trigger MissingGreenlet with
multi-stack taxes (IVA addition + Retefuente withholding on the same line).

Bug: POST /sales-orders with two tax_rate_ids on a single line raised
`sqlalchemy.exc.MissingGreenlet` because the SO fetch options only loaded
`SalesOrderLine.line_taxes` but not the nested `line_tax.rate` and
`rate.category` relationships that `recalculate_so_totals` walks.

Fix: extend _SO_OPTIONS in sales_order_repo.py to chain:
    selectinload(SalesOrder.lines)
      .selectinload(SalesOrderLine.line_taxes)
      .selectinload(SalesOrderLineTax.rate)
      .selectinload(TaxRate.category)

This arithmetic test uses plain SimpleNamespace objects — it pins the
behavior of `recalculate_so_totals` once the category chain is present,
proving the service logic is correct so the only failure mode left is
lazy loading, which the repo-level fix now prevents.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.services.sales_order_service import recalculate_so_totals


def _mk_rate(rate_value: str, behavior: str, base_kind: str = "subtotal"):
    cat = SimpleNamespace(behavior=behavior, base_kind=base_kind)
    return SimpleNamespace(rate=Decimal(rate_value), category=cat)


def _mk_line_tax(rate):
    # Mutable namespace: recalculate assigns rate_pct / base_amount / tax_amount / behavior
    return SimpleNamespace(
        rate=rate,
        rate_pct=Decimal("0"),
        base_amount=Decimal("0"),
        tax_amount=Decimal("0"),
        behavior="",
    )


def test_recalculate_so_totals_iva_plus_retefuente_no_greenlet() -> None:
    """IVA 19% (addition) + Retefuente 4% (withholding) on a 1000 line.

    Expected:
      - line.tax_amount          = 190.00  (IVA)
      - line.retention_amount    = 40.00   (Retefuente)
      - line.line_total_with_tax = 1190.00
      - so.total_with_tax        = 1190.00
      - so.total_payable         = 1150.00 (1190 - 40)
    """
    iva = _mk_rate("0.19", "addition")
    retefuente = _mk_rate("0.04", "withholding")

    line = SimpleNamespace(
        qty_ordered=Decimal("10"),
        unit_price=Decimal("100.00"),
        discount_pct=Decimal("0"),
        discount_amount=Decimal("0"),
        line_subtotal=Decimal("1000.00"),
        line_total=Decimal("0"),
        tax_rate=None,
        tax_rate_pct=None,
        retention_pct=None,
        tax_amount=Decimal("0"),
        retention_amount=Decimal("0"),
        line_total_with_tax=Decimal("0"),
        line_taxes=[_mk_line_tax(iva), _mk_line_tax(retefuente)],
    )
    so = SimpleNamespace(
        lines=[line],
        discount_pct=Decimal("0"),
        discount_amount=Decimal("0"),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("0"),
        total=Decimal("0"),
        total_retention=Decimal("0"),
        total_with_tax=Decimal("0"),
        total_payable=Decimal("0"),
    )

    # Should NOT raise MissingGreenlet — all relationship-like attrs are resolved
    recalculate_so_totals(so)

    assert line.tax_amount == Decimal("190.00")
    assert line.retention_amount == Decimal("40.00")
    assert line.line_total_with_tax == Decimal("1190.0000")
    assert so.total_with_tax == Decimal("1190.00")
    assert so.total_retention == Decimal("40.00")
    assert so.total_payable == Decimal("1150.00")


def test_recalculate_so_totals_multi_stack_two_additions() -> None:
    """Two addition-behavior taxes on one line (non-cumulative)."""
    iva = _mk_rate("0.19", "addition")
    inc = _mk_rate("0.02", "addition")  # hypothetical 2% municipal

    line = SimpleNamespace(
        qty_ordered=Decimal("5"),
        unit_price=Decimal("100.00"),
        discount_pct=Decimal("0"),
        discount_amount=Decimal("0"),
        line_subtotal=Decimal("500.00"),
        line_total=Decimal("0"),
        tax_rate=None,
        tax_rate_pct=None,
        retention_pct=None,
        tax_amount=Decimal("0"),
        retention_amount=Decimal("0"),
        line_total_with_tax=Decimal("0"),
        line_taxes=[_mk_line_tax(iva), _mk_line_tax(inc)],
    )
    so = SimpleNamespace(
        lines=[line],
        discount_pct=Decimal("0"),
        discount_amount=Decimal("0"),
        subtotal=Decimal("500.00"),
        tax_amount=Decimal("0"),
        total=Decimal("0"),
        total_retention=Decimal("0"),
        total_with_tax=Decimal("0"),
        total_payable=Decimal("0"),
    )

    recalculate_so_totals(so)

    # 500 * 0.19 = 95; 500 * 0.02 = 10 → 105 total addition
    assert line.tax_amount == Decimal("105.00")
    assert line.retention_amount == Decimal("0")
    assert so.total_with_tax == Decimal("605.00")
    assert so.total_payable == Decimal("605.00")
