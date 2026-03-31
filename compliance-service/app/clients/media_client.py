"""HTTP client for media-service — centralized file management.

All functions are non-fatal: return None/False on failure, never raise.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.core.settings import get_settings

_http_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
    return _http_client


def _base_url() -> str:
    return get_settings().MEDIA_SERVICE_URL.rstrip("/")


def _s2s_headers() -> dict[str, str]:
    return {"X-Service-Token": get_settings().S2S_SERVICE_TOKEN}


async def upload_file(
    *,
    tenant_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    category: str = "general",
    document_type: str | None = None,
    title: str | None = None,
    uploaded_by: str | None = None,
) -> dict[str, Any] | None:
    """Upload a file to media-service. Returns file metadata dict or None on failure."""
    try:
        client = _get_client()
        params: dict[str, str] = {"tenant_id": tenant_id, "category": category}
        if document_type:
            params["document_type"] = document_type
        if title:
            params["title"] = title
        if uploaded_by:
            params["uploaded_by"] = uploaded_by

        resp = await client.post(
            f"{_base_url()}/api/v1/internal/media/files",
            headers=_s2s_headers(),
            params=params,
            files={"file": (filename, file_bytes, content_type)},
        )
        if resp.status_code == 201:
            return resp.json()
        return None
    except Exception:
        return None


async def get_file(tenant_id: str, file_id: str) -> dict[str, Any] | None:
    """Get file metadata from media-service."""
    try:
        client = _get_client()
        resp = await client.get(
            f"{_base_url()}/api/v1/internal/media/files/{file_id}",
            headers=_s2s_headers(),
            params={"tenant_id": tenant_id},
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


async def list_files(
    tenant_id: str,
    category: str | None = None,
    document_type: str | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List media files for a tenant."""
    try:
        client = _get_client()
        params: dict[str, Any] = {"tenant_id": tenant_id, "offset": offset, "limit": limit}
        if category:
            params["category"] = category
        if document_type:
            params["document_type"] = document_type
        if search:
            params["search"] = search

        resp = await client.get(
            f"{_base_url()}/api/v1/internal/media/files",
            headers=_s2s_headers(),
            params=params,
        )
        if resp.status_code == 200:
            return resp.json().get("items", [])
        return []
    except Exception:
        return []


async def delete_file(tenant_id: str, file_id: str) -> bool:
    """Delete a file from media-service."""
    try:
        client = _get_client()
        resp = await client.delete(
            f"{_base_url()}/api/v1/internal/media/files/{file_id}",
            headers=_s2s_headers(),
            params={"tenant_id": tenant_id},
        )
        return resp.status_code == 204
    except Exception:
        return False


async def validate_file_ids(tenant_id: str, file_ids: list[str]) -> list[str]:
    """Check which file IDs exist in media-service. Returns valid IDs."""
    try:
        client = _get_client()
        resp = await client.post(
            f"{_base_url()}/api/v1/internal/media/files/validate",
            headers=_s2s_headers(),
            json={"tenant_id": tenant_id, "file_ids": file_ids},
        )
        if resp.status_code == 200:
            return resp.json().get("valid_ids", [])
        return []
    except Exception:
        return []


async def close_client() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
