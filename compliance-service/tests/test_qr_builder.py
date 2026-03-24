"""Unit tests for QR code generation."""
from __future__ import annotations

import base64

import pytest
from app.certificates.qr_builder import generate_qr, generate_qr_base64


class TestGenerateQR:
    def test_returns_bytes(self):
        result = generate_qr("https://verify.tracelog.co/cert/TL-2026-000001")
        assert isinstance(result, bytes)

    def test_returns_png(self):
        result = generate_qr("https://example.com")
        # PNG magic bytes
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_non_empty(self):
        result = generate_qr("https://example.com")
        assert len(result) > 100  # a QR PNG is at least a few KB

    def test_different_urls_different_output(self):
        qr1 = generate_qr("https://example.com/1")
        qr2 = generate_qr("https://example.com/2")
        assert qr1 != qr2


class TestGenerateQRBase64:
    def test_returns_data_uri(self):
        result = generate_qr_base64("https://example.com")
        assert result.startswith("data:image/png;base64,")

    def test_decodable(self):
        result = generate_qr_base64("https://example.com")
        b64_part = result.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"
