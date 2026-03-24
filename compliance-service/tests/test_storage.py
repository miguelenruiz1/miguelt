"""Unit tests for certificate storage backends."""
from __future__ import annotations

import os
import tempfile

import pytest
from app.certificates.storage import LocalStorage


class TestLocalStorage:
    def test_upload_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage()
            storage.BASE_DIR = type(storage.BASE_DIR)(tmpdir)

            import asyncio
            url = asyncio.get_event_loop().run_until_complete(
                storage.upload(
                    tenant_id="test-tenant",
                    year=2026,
                    filename="TL-2026-000001.pdf",
                    data=b"fake PDF content",
                )
            )

            expected_path = os.path.join(tmpdir, "test-tenant", "2026", "TL-2026-000001.pdf")
            assert os.path.exists(expected_path)
            with open(expected_path, "rb") as f:
                assert f.read() == b"fake PDF content"
            assert "TL-2026-000001.pdf" in url

    def test_upload_creates_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage()
            storage.BASE_DIR = type(storage.BASE_DIR)(tmpdir)

            import asyncio
            asyncio.get_event_loop().run_until_complete(
                storage.upload(
                    tenant_id="deep-tenant",
                    year=2026,
                    filename="cert.pdf",
                    data=b"test",
                )
            )
            assert os.path.exists(os.path.join(tmpdir, "deep-tenant", "2026", "cert.pdf"))
