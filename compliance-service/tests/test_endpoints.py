"""Integration tests for compliance-service endpoints via HTTP.

These tests hit the running service at localhost:9005.
Requires: docker compose up compliance-api
"""
from __future__ import annotations

import httpx
import pytest

import os

BASE = os.environ.get("TEST_BASE_URL", "http://localhost:8005")


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=10.0) as c:
        yield c


class TestHealth:
    def test_health(self, client: httpx.Client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_ready(self, client: httpx.Client):
        r = client.get("/ready")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "ready")
        assert "checks" in data


class TestPublicVerify:
    def test_verify_nonexistent_cert(self, client: httpx.Client):
        r = client.get("/api/v1/compliance/verify/TL-9999-999999")
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is False
        assert data["status"] == "not_found"
        assert data["certificate_number"] == "TL-9999-999999"

    def test_verify_no_tenant_header_needed(self, client: httpx.Client):
        """Public endpoint should not require X-Tenant-Id."""
        r = client.get("/api/v1/compliance/verify/TL-2026-000001")
        assert r.status_code == 200  # not 400 or 422


class TestAuthRequired:
    def test_frameworks_without_auth_returns_401(self, client: httpx.Client):
        r = client.get(
            "/api/v1/compliance/frameworks/",
            headers={"X-Tenant-Id": "default"},
        )
        assert r.status_code == 401

    def test_plots_without_auth_returns_401(self, client: httpx.Client):
        r = client.get(
            "/api/v1/compliance/plots/",
            headers={"X-Tenant-Id": "default"},
        )
        assert r.status_code == 401

    def test_records_without_auth_returns_401(self, client: httpx.Client):
        r = client.get(
            "/api/v1/compliance/records/",
            headers={"X-Tenant-Id": "default"},
        )
        assert r.status_code == 401

    def test_certificates_without_auth_returns_401(self, client: httpx.Client):
        r = client.get(
            "/api/v1/compliance/certificates",
            headers={"X-Tenant-Id": "default"},
        )
        assert r.status_code == 401


class TestOpenAPI:
    def test_openapi_json_accessible(self, client: httpx.Client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert "paths" in data
        # Check key paths exist
        paths = data["paths"]
        assert "/api/v1/compliance/frameworks/" in paths
        assert "/api/v1/compliance/records/" in paths
        assert "/api/v1/compliance/plots/" in paths
        assert "/api/v1/compliance/certificates" in paths
        assert "/api/v1/compliance/verify/{certificate_number}" in paths

    def test_docs_page_accessible(self, client: httpx.Client):
        r = client.get("/docs")
        assert r.status_code == 200
