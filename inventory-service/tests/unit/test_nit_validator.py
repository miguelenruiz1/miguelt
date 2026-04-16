"""Unit tests for Colombian NIT (tax ID) validation.

The DIAN check digit algorithm is deterministic — no DB or I/O needed.
"""
from __future__ import annotations

import pytest

from app.utils.nit import compute_nit_check_digit, is_valid_nit, assert_valid_nit


class TestComputeCheckDigit:
    def test_nit_bancolombia(self) -> None:
        # 800197268-4 is Bancolombia's publicly listed NIT
        assert compute_nit_check_digit("800197268") == 4

    def test_nit_accepts_dots(self) -> None:
        # 900.123.456 is cleaned to 900123456 -> DV = 8
        assert compute_nit_check_digit("900.123.456") == 8

    def test_nit_invalid_non_digit_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_nit_check_digit("abc")

    def test_nit_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_nit_check_digit("")


class TestIsValidNit:
    def test_nit_valid_digit_verificador(self) -> None:
        """Real NIT with correct check digit → valid."""
        assert is_valid_nit("900123456-8") is True

    def test_nit_invalid_digit_verificador(self) -> None:
        """Same base with wrong DV → invalid."""
        assert is_valid_nit("900123456-3") is False

    def test_nit_without_dash_invalid(self) -> None:
        assert is_valid_nit("900123456") is False

    def test_nit_with_dots_and_valid_dv(self) -> None:
        assert is_valid_nit("900.123.456-8") is True

    def test_nit_none_safe(self) -> None:
        assert is_valid_nit("") is False

    def test_assert_valid_nit_raises_on_bad(self) -> None:
        with pytest.raises(ValueError, match="Invalid NIT"):
            assert_valid_nit("900123456-3")

    def test_assert_valid_nit_passes_on_good(self) -> None:
        # Should not raise
        assert_valid_nit("900123456-8")
