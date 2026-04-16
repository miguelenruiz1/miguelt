"""TOTP helpers tests (FASE4).

We test the pure-python parts of TOTPService without DB dependency by
exercising pyotp directly to validate our secret/code format assumptions.
"""
from __future__ import annotations

import pyotp

from app.services.totp_service import (
    ISSUER,
    RECOVERY_CODE_COUNT,
    RECOVERY_CODE_LEN,
    _gen_recovery_code,
)


def test_recovery_code_shape():
    c = _gen_recovery_code()
    assert len(c) == RECOVERY_CODE_LEN
    assert c.isalnum()
    assert c.isupper() or any(ch.isdigit() for ch in c)


def test_recovery_codes_unique_batch():
    codes = [_gen_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]
    # Extremely unlikely to collide with 36^10 space, but sanity.
    assert len(set(codes)) == RECOVERY_CODE_COUNT


def test_totp_roundtrip():
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    code = totp.now()
    assert totp.verify(code)


def test_provisioning_uri_shape():
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(name="a@b.com", issuer_name=ISSUER)
    assert uri.startswith("otpauth://totp/")
    assert f"issuer={ISSUER}" in uri
    assert "secret=" in uri


def test_issuer_is_trace():
    assert ISSUER == "Trace"
