"""NIT (Colombian tax ID) validation.

A NIT is formatted as 'XXXXXXXXX-D' where D is the check digit calculated
via DIAN's weighted-sum algorithm (see Estatuto Tributario art. 555-1).

Weights (positional, right-to-left, excluding the check digit):
    [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]

Algorithm:
    1. Strip dots/spaces. Split on '-' to separate check digit.
    2. Multiply each digit of the base (right-to-left) by its weight.
    3. Sum = modulo 11. If result in {0, 1} → check digit = result.
       Otherwise → check digit = 11 - result.
"""
from __future__ import annotations

__all__ = ["compute_nit_check_digit", "is_valid_nit", "assert_valid_nit"]

_WEIGHTS: tuple[int, ...] = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


def _clean(base: str) -> str:
    return base.replace(".", "").replace(" ", "").replace(",", "").strip()


def compute_nit_check_digit(base_number: str) -> int:
    """Compute the DIAN check digit for a NIT base (no dashes/dots).

    Raises ValueError if the input contains non-digit chars or is empty.
    """
    digits = _clean(base_number)
    if not digits or not digits.isdigit():
        raise ValueError(f"NIT base must be digits only, got {base_number!r}")
    total = 0
    # right-to-left: rightmost digit pairs with weights[0] = 3
    for idx, ch in enumerate(reversed(digits)):
        if idx >= len(_WEIGHTS):
            raise ValueError("NIT base too long (max 15 digits)")
        total += int(ch) * _WEIGHTS[idx]
    remainder = total % 11
    if remainder in (0, 1):
        return remainder
    return 11 - remainder


def is_valid_nit(nit: str) -> bool:
    """Return True iff `nit` is 'BASE-D' with D matching the computed digit."""
    try:
        cleaned = _clean(nit)
        if "-" not in cleaned:
            return False
        base, check = cleaned.rsplit("-", 1)
        if not check.isdigit() or not base.isdigit():
            return False
        return compute_nit_check_digit(base) == int(check)
    except (ValueError, AttributeError):
        return False


def assert_valid_nit(nit: str) -> None:
    """Raise ValueError if `nit` is not a valid NIT."""
    if not is_valid_nit(nit):
        raise ValueError(f"Invalid NIT: {nit!r}")
