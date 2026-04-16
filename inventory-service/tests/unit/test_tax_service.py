"""Unit tests for TaxService — pure math + ConflictError validation.

The `calculate_line_taxes` staticmethod is called from `recalculate_so_taxes`
and is the load-bearing piece of arithmetic. These tests exercise it without
any DB so they stay fast and deterministic.

The `create_rate` ConflictError test uses AsyncMock to stub the DB execute
calls, avoiding the need for a real Postgres.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.tax_service import TaxService, CO_ALLOWED_TAX_SLUGS


# ── Pure arithmetic ─────────────────────────────────────────────────────────


class TestCalculateLineTaxes:
    def test_recalculate_so_taxes_single_iva_addition(self) -> None:
        """Single line with IVA 19% → tax = subtotal * 0.19."""
        result = TaxService.calculate_line_taxes(
            subtotal=Decimal("100.00"),
            tax_rate=Decimal("0.19"),
        )
        assert result["tax_amount"] == Decimal("19.00")
        assert result["retention_amount"] == Decimal("0")
        assert result["line_total_with_tax"] == Decimal("119.00")

    def test_recalculate_so_taxes_iva_plus_retefuente(self) -> None:
        """IVA 19% addition + Retefuente 4% withholding."""
        result = TaxService.calculate_line_taxes(
            subtotal=Decimal("1000.00"),
            tax_rate=Decimal("0.19"),
            retention_rate=Decimal("0.04"),
        )
        assert result["tax_amount"] == Decimal("190.00")
        assert result["retention_amount"] == Decimal("40.00")
        # total_with_tax = subtotal + addition (retention is NOT added in this helper)
        assert result["line_total_with_tax"] == Decimal("1190.00")

    def test_recalculate_so_taxes_multi_line(self) -> None:
        """Aggregating 3 hypothetical lines — arithmetic stays exact."""
        totals = [
            TaxService.calculate_line_taxes(Decimal("100"), Decimal("0.19")),
            TaxService.calculate_line_taxes(Decimal("250"), Decimal("0.05")),
            TaxService.calculate_line_taxes(Decimal("40"),  Decimal("0.00")),
        ]
        total_tax = sum((t["tax_amount"] for t in totals), Decimal("0"))
        assert total_tax == Decimal("19.00") + Decimal("12.50") + Decimal("0.00")
        assert total_tax == Decimal("31.50")

    def test_tax_rate_zero_exempt(self) -> None:
        """IVA 0% (exento) → no tax, subtotal preserved."""
        result = TaxService.calculate_line_taxes(
            subtotal=Decimal("500.00"),
            tax_rate=Decimal("0"),
        )
        assert result["tax_amount"] == Decimal("0.00")
        assert result["line_total_with_tax"] == Decimal("500.00")

    def test_rounding_half_up(self) -> None:
        """Half-up rounding convention."""
        result = TaxService.calculate_line_taxes(
            subtotal=Decimal("33.33"),
            tax_rate=Decimal("0.19"),
        )
        # 33.33 * 0.19 = 6.3327 → 6.33
        assert result["tax_amount"] == Decimal("6.33")


# ── ConflictError on non-CO tax slug ────────────────────────────────────────


class TestCreateRateColombiaMVP:
    def test_co_allowed_slugs_frozen(self) -> None:
        """Defensive check: only IVA + Retefuente allowed in Colombia MVP."""
        assert CO_ALLOWED_TAX_SLUGS == frozenset({"iva", "retefuente"})
        assert "gst" not in CO_ALLOWED_TAX_SLUGS
        assert "vat" not in CO_ALLOWED_TAX_SLUGS

    @pytest.mark.asyncio
    async def test_create_rate_rejects_non_co_slug(self) -> None:
        """A TaxCategory with slug='gst' must raise ConflictError."""
        from app.core.errors import ConflictError

        # Mock DB: return a fake TaxCategory with slug='gst'
        fake_category = SimpleNamespace(id="cat-1", slug="gst")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_category

        db = MagicMock()
        db.execute = AsyncMock(return_value=result_mock)

        svc = TaxService(db)
        with pytest.raises(ConflictError, match="Colombia MVP"):
            await svc.create_rate(
                tenant_id="t-1",
                data={"category_id": "cat-1", "name": "GST 10%", "rate": 0.10},
            )
