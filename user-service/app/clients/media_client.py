"""HTTP client for media-service — centralized file management."""
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
