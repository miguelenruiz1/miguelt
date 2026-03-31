"""HTTP client for trace-service Anchoring-as-a-Service API.

Fire-and-forget pattern: anchoring failures are non-fatal to inventory operations.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

_http_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    return _http_client


def _base_url() -> str:
    return get_settings().TRACE_SERVICE_URL.rstrip("/")


async def anchor_event(
    *,
    tenant_id: str,
    source_entity_type: str,
    source_entity_id: str,
    payload_hash: str,
    callback_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Submit a hash to trace-service for Solana anchoring.
    Fire-and-forget: returns None on failure, never raises.
    """
    try:
        client = _get_client()
        resp = await client.post(
            f"{_base_url()}/api/v1/anchoring/hash",
            json={
                "tenant_id": tenant_id,
                "source_service": "inventory-service",
                "source_entity_type": source_entity_type,
                "source_entity_id": source_entity_id,
                "payload_hash": payload_hash,
                "callback_url": callback_url,
                "metadata": metadata or {},
            },
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            log.info(
                "anchor_submitted",
                entity=f"{source_entity_type}/{source_entity_id}",
                hash=payload_hash[:16],
                status=data.get("anchor_status"),
            )
            return data
        else:
            log.warning(
                "anchor_submit_failed",
                status_code=resp.status_code,
                body=resp.text[:200],
            )
            return None
    except Exception as exc:
        log.warning("anchor_submit_error", exc=str(exc))
        return None


async def anchor_event_background(
    *,
    tenant_id: str,
    source_entity_type: str,
    source_entity_id: str,
    payload_hash: str,
    callback_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Fire-and-forget wrapper — launches anchor_event as a background task."""
    asyncio.create_task(
        anchor_event(
            tenant_id=tenant_id,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            payload_hash=payload_hash,
            callback_url=callback_url,
            metadata=metadata,
        )
    )


async def get_anchor_status(payload_hash: str) -> dict[str, Any] | None:
    """Query the anchoring status of a hash. Returns None on failure."""
    try:
        client = _get_client()
        resp = await client.get(f"{_base_url()}/api/v1/anchoring/{payload_hash}/status")
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as exc:
        log.warning("anchor_status_error", exc=str(exc))
        return None


async def verify_anchor(payload_hash: str) -> dict[str, Any] | None:
    """Verify a hash is anchored on Solana. Returns None on failure."""
    try:
        client = _get_client()
        resp = await client.post(
            f"{_base_url()}/api/v1/anchoring/verify",
            json={"payload_hash": payload_hash},
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as exc:
        log.warning("anchor_verify_error", exc=str(exc))
        return None


async def mint_batch_cnft(
    *,
    tenant_id: str,
    batch_id: str,
    batch_number: str,
    product_name: str,
    product_type: str | None = None,
    manufacture_date: str | None = None,
    expiration_date: str | None = None,
    supplier: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Request trace-service to mint a cNFT for a batch.
    Uses trace-service's existing POST /api/v1/assets/mint endpoint.
    Returns mint result or None on failure. Never raises.
    """
    try:
        client = _get_client()
        mint_metadata = {
            "type": "inventory_batch",
            "batch_id": batch_id,
            "batch_number": batch_number,
            "product_name": product_name,
            "product_type": product_type or "general",
            "manufacture_date": manufacture_date,
            "expiration_date": expiration_date,
            "supplier": supplier,
            **(metadata or {}),
        }
        resp = await client.post(
            f"{_base_url()}/api/v1/assets/mint",
            json={
                "product_type": product_type or "inventory_batch",
                "metadata": mint_metadata,
            },
            headers={
                "X-Tenant-Id": tenant_id,
                "X-User-Id": "1",
            },
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            log.info(
                "batch_cnft_minted",
                batch_id=batch_id,
                asset_id=data.get("id"),
                blockchain_status=data.get("blockchain_status"),
            )
            return data
        else:
            log.warning("batch_cnft_mint_failed", status_code=resp.status_code, body=resp.text[:200])
            return None
    except Exception as exc:
        log.warning("batch_cnft_mint_error", exc=str(exc))
        return None


def _s2s_headers() -> dict[str, str]:
    return {"X-Service-Token": get_settings().S2S_SERVICE_TOKEN}


async def notify_po_received(
    *,
    tenant_id: str,
    po_id: str,
    entity_id: str,
    warehouse_id: str,
    quantity: int,
    batch_id: str | None = None,
) -> dict[str, Any] | None:
    """
    Fire-and-forget: notify trace-service that a PO was received.
    Creates an Asset in trace with initial workflow state.
    """
    try:
        client = _get_client()
        resp = await client.post(
            f"{_base_url()}/api/v1/internal/assets/from-po-receipt",
            json={
                "po_id": po_id,
                "entity_id": entity_id,
                "batch_id": batch_id,
                "warehouse_id": warehouse_id,
                "tenant_id": tenant_id,
                "quantity": quantity,
            },
            headers=_s2s_headers(),
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            log.info(
                "trace_po_receipt_notified",
                po_id=po_id,
                asset_id=data.get("asset_id"),
            )
            return data
        else:
            log.warning("trace_po_receipt_failed", status_code=resp.status_code, body=resp.text[:200])
            return None
    except Exception as exc:
        log.warning("trace_po_receipt_error", exc=str(exc))
        return None


async def notify_po_received_background(
    **kwargs: Any,
) -> None:
    """Fire-and-forget wrapper — launches as background task."""
    asyncio.create_task(notify_po_received(**kwargs))


async def notify_so_shipped(
    *,
    tenant_id: str,
    so_id: str,
    asset_ids: list[str],
    to_wallet_id: str,
    tracking_number: str | None = None,
) -> dict[str, Any] | None:
    """
    Fire-and-forget: notify trace-service that a SO was shipped.
    Performs handoff on each asset.
    """
    try:
        client = _get_client()
        resp = await client.post(
            f"{_base_url()}/api/v1/internal/assets/handoff-from-so",
            json={
                "so_id": so_id,
                "asset_ids": asset_ids,
                "to_wallet_id": to_wallet_id,
                "tracking_number": tracking_number,
                "tenant_id": tenant_id,
            },
            headers=_s2s_headers(),
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            log.info(
                "trace_so_shipped_notified",
                so_id=so_id,
                handoffs=len(data.get("handoffs", [])),
                errors=len(data.get("errors", [])),
            )
            return data
        else:
            log.warning("trace_so_shipped_failed", status_code=resp.status_code, body=resp.text[:200])
            return None
    except Exception as exc:
        log.warning("trace_so_shipped_error", exc=str(exc))
        return None


async def notify_so_shipped_background(
    **kwargs: Any,
) -> None:
    """Fire-and-forget wrapper — launches as background task."""
    asyncio.create_task(notify_so_shipped(**kwargs))


async def close_client() -> None:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
