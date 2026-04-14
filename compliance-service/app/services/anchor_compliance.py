"""Anchor EUDR screening results to Solana via trace-service.

Two actions per screening:
1. **Anchor hash** — ``POST /anchoring/hash`` records the SHA-256 of the
   canonical screening payload on Solana via the Memo Program.
2. **Custody event** — ``POST /assets/{id}/events`` creates an informational
   ``COMPLIANCE_VERIFIED`` event on the asset's custody chain so auditors
   see it alongside handoffs, arrivals, etc.

Both calls are best-effort: if trace-service is down, the screening result
is still saved in PostgreSQL and can be anchored later.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.utils.json_canonical import canonical_json_bytes

log = get_logger(__name__)


def compute_compliance_hash(screening_result: dict[str, Any]) -> str:
    """Compute SHA-256 hex digest of a canonical screening result."""
    raw = canonical_json_bytes(screening_result)
    return hashlib.sha256(raw).hexdigest()


async def anchor_screening_result(
    *,
    http: httpx.AsyncClient,
    tenant_id: uuid.UUID,
    asset_id: uuid.UUID,
    plot_id: uuid.UUID,
    plot_code: str,
    screening_result: dict[str, Any],
    user_id: str = "system",
) -> dict[str, Any]:
    """Anchor a screening result to Solana and create a custody event.

    Returns a dict with ``compliance_hash``, ``anchor_request_id`` (may be
    None on failure), and ``event_id`` (may be None on failure).
    """
    settings = get_settings()
    base = settings.TRACE_SERVICE_URL.rstrip("/")
    s2s_token = settings.S2S_SERVICE_TOKEN
    compliance_hash = compute_compliance_hash(screening_result)

    headers = {
        "X-Tenant-Id": str(tenant_id),
        "X-User-Id": user_id,
        "X-Service-Token": s2s_token,
        "Content-Type": "application/json",
    }

    anchor_request_id: str | None = None
    event_id: str | None = None

    # ── 1. Anchor hash via Anchoring-as-a-Service ────────────────────────────
    try:
        resp = await http.post(
            f"{base}/api/v1/anchoring/hash",
            headers=headers,
            json={
                "tenant_id": str(tenant_id),
                "source_service": "compliance-service",
                "source_entity_type": "eudr_screening",
                "source_entity_id": str(plot_id),
                "payload_hash": compliance_hash,
                "callback_url": (
                    f"{settings.PUBLIC_BASE_URL}/api/v1/compliance/plots/"
                    f"{plot_id}/anchor-callback"
                ),
                "metadata": {
                    "plot_id": str(plot_id),
                    "plot_code": plot_code,
                    "asset_id": str(asset_id),
                    "screening_type": "eudr_full",
                    "eudr_risk": screening_result.get("eudr_risk"),
                    "eudr_compliant": screening_result.get("eudr_compliant"),
                },
            },
            timeout=10.0,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            anchor_request_id = data.get("id")
            log.info(
                "anchor_hash_submitted",
                anchor_id=anchor_request_id,
                compliance_hash=compliance_hash[:16],
                plot_id=str(plot_id),
            )
        else:
            log.warning("anchor_hash_failed", status=resp.status_code, body=resp.text[:300])
    except Exception as exc:
        log.warning("anchor_hash_error", exc=str(exc), plot_id=str(plot_id))

    # ── 2. Create COMPLIANCE_VERIFIED custody event on the asset ─────────────
    try:
        resp = await http.post(
            f"{base}/api/v1/assets/{asset_id}/events",
            headers=headers,
            json={
                "event_type": "COMPLIANCE_VERIFIED",
                "data": {
                    "compliance_hash": compliance_hash,
                    "plot_id": str(plot_id),
                    "plot_code": plot_code,
                    "eudr_compliant": screening_result.get("eudr_compliant"),
                    "eudr_risk": screening_result.get("eudr_risk"),
                    "risk_reason": screening_result.get("risk_reason"),
                    "sources": list(screening_result.get("sources", {}).keys()),
                    "failed_sources": screening_result.get("failed_sources", []),
                    "screening_checked_at": screening_result.get("checked_at"),
                },
                "notes": (
                    f"Screening EUDR multi-fuente completado para parcela {plot_code}. "
                    f"Riesgo: {screening_result.get('eudr_risk', '?')}. "
                    f"Hash: {compliance_hash[:16]}..."
                ),
            },
            timeout=10.0,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            event_id = data.get("event", {}).get("id")
            log.info(
                "compliance_event_created",
                event_id=event_id,
                asset_id=str(asset_id),
                plot_id=str(plot_id),
            )
        else:
            log.warning(
                "compliance_event_failed",
                status=resp.status_code,
                body=resp.text[:300],
                asset_id=str(asset_id),
            )
    except Exception as exc:
        log.warning("compliance_event_error", exc=str(exc), asset_id=str(asset_id))

    return {
        "compliance_hash": compliance_hash,
        "anchor_request_id": anchor_request_id,
        "event_id": event_id,
        "anchor_status": "pending" if anchor_request_id else "failed",
    }
