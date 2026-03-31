"""Lightweight HTTP client to emit events to integration-service for webhook dispatch.

Usage:
    from app.clients.webhook_client import emit_event
    await emit_event("inventory.so.shipped", tenant_id, {"order_id": "...", ...})

All calls are fire-and-forget — failures are logged but never raise.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.core.settings import get_settings

_http: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(timeout=5.0)
    return _http


async def emit_event(
    event_type: str,
    tenant_id: str,
    payload: dict[str, Any],
    source_service: str = "inventory-service",
) -> None:
    """Fire-and-forget: send event to integration-service for webhook dispatch."""
    try:
        settings = get_settings()
        url = getattr(settings, "INTEGRATION_SERVICE_URL", "http://integration-api:8004")
        client = _get_client()
        await client.post(
            f"{url}/api/v1/internal/events",
            json={
                "event_type": event_type,
                "payload": payload,
                "source_service": source_service,
            },
            headers={"X-Tenant-Id": tenant_id},
        )
    except Exception:
        pass  # fire-and-forget, never block the caller
