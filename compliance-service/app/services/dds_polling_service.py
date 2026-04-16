"""Background polling loop for DDS validation status.

Scans compliance_records with declaration_status='submitted' at regular
intervals and calls TRACES NT retrieveDdsInfoByReferences to pick up the
EU-side verdict. On the first transition to 'validated' we also notify the
operator (buyer) by email.

Isolated from the request path so latency spikes in TRACES NT don't affect
user-facing calls; runs inside the compliance-service lifespan as a task.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_, or_, select

from app.core.logging import get_logger
from app.models.record import ComplianceRecord
from app.services.email_client import get_email_client
from app.services.traces_service import TracesNTService

log = get_logger(__name__)

POLL_INTERVAL_SECONDS_DEFAULT = 60
POLL_MIN_SPACING_SECONDS = 60
BATCH_LIMIT = 50

_TEMPLATE_PATH = Path(__file__).parent / "email_templates" / "dds_validated.html"


def _render_template(context: dict[str, Any]) -> str:
    """Minimal {{var}} replacement — no Jinja dependency."""
    tpl = _TEMPLATE_PATH.read_text(encoding="utf-8")
    for key, val in context.items():
        tpl = tpl.replace("{{" + key + "}}", str(val or ""))
    return tpl


def _traces_portal_url(reference_number: str) -> str:
    # EU portal URL; leaves the tenant free to deep-link elsewhere if needed.
    return f"https://webgate.ec.europa.eu/tracesnt/directory/dds/{reference_number}"


async def _notify_validated(record: ComplianceRecord) -> None:
    """Send the 'DDS validated' email to the operator (buyer)."""
    # EU side: the buyer/operator is the one who cares about DDS validation.
    # Fall back to supplier_email only if no buyer_email is set.
    recipient = (record.buyer_email or record.supplier_email or "").strip()
    if not recipient:
        log.warning(
            "dds_validated_no_recipient",
            record_id=str(record.id),
            reference=record.declaration_reference,
        )
        return

    validated_at = (
        record.declaration_validated_at.strftime("%Y-%m-%d %H:%M UTC")
        if record.declaration_validated_at
        else "—"
    )
    ctx = {
        "recipient_name": record.buyer_name or record.supplier_name or "operador",
        "reference_number": record.declaration_reference or "—",
        "commodity": record.product_description or record.commodity_type or "—",
        "quantity": str(record.quantity_kg) if record.quantity_kg else "—",
        "validated_at": validated_at,
        "country_of_production": record.country_of_production or "—",
        "traces_url": _traces_portal_url(record.declaration_reference or ""),
    }
    try:
        html_body = _render_template(ctx)
    except Exception as exc:
        log.exception("dds_validated_render_failed", record_id=str(record.id), error=str(exc))
        return

    client = get_email_client()
    result = await client.send(
        tenant_id=str(record.tenant_id),
        to=recipient,
        subject=f"DDS validada — Reference {record.declaration_reference}",
        html_body=html_body,
    )
    if result.success:
        log.info(
            "dds_validated_email_sent",
            record_id=str(record.id),
            to=recipient,
            message_id=result.message_id,
        )
    else:
        log.warning(
            "dds_validated_email_failed",
            record_id=str(record.id),
            to=recipient,
            error_code=result.error_code,
            error_message=(result.error_message or "")[:200],
        )


async def poll_once(db) -> dict[str, Any]:
    """Run a single polling pass. Returns a summary dict.

    Shape: {scanned, validated, rejected, amended, unchanged, errors}.
    """
    now = datetime.now(tz=timezone.utc)
    threshold = now - timedelta(seconds=POLL_MIN_SPACING_SECONDS)

    stmt = (
        select(ComplianceRecord)
        .where(
            ComplianceRecord.declaration_status == "submitted",
            ComplianceRecord.declaration_reference.is_not(None),
            or_(
                ComplianceRecord.declaration_last_polled_at.is_(None),
                ComplianceRecord.declaration_last_polled_at < threshold,
            ),
        )
        .limit(BATCH_LIMIT)
    )

    records = list((await db.execute(stmt)).scalars().all())
    summary = {
        "scanned": len(records),
        "validated": 0,
        "rejected": 0,
        "amended": 0,
        "unchanged": 0,
        "errors": 0,
    }

    if not records:
        return summary

    # Cache one TracesNTService per tenant (they load creds per tenant).
    svc_cache: dict[str, TracesNTService] = {}
    for rec in records:
        try:
            tenant_key = str(rec.tenant_id)
            svc = svc_cache.get(tenant_key)
            if svc is None:
                svc = await TracesNTService.from_db(db, tenant_id=rec.tenant_id)
                svc_cache[tenant_key] = svc

            if not svc.is_configured:
                # Tenant has no creds — skip, avoid spamming logs.
                summary["unchanged"] += 1
                continue

            info = await svc.retrieve_dds_info(rec.declaration_reference)
            rec.declaration_last_polled_at = now

            if not info.get("ok"):
                summary["errors"] += 1
                continue

            new_status = info.get("status")
            if new_status == "validated" and rec.declaration_status != "validated":
                rec.declaration_status = "validated"
                rec.declaration_validated_at = now
                rec.declaration_rejection_reason = None
                summary["validated"] += 1
                # Notify the operator — don't fail the whole loop if email throws.
                try:
                    await _notify_validated(rec)
                except Exception:
                    log.exception("dds_validated_notify_error", record_id=str(rec.id))
            elif new_status == "rejected" and rec.declaration_status != "rejected":
                rec.declaration_status = "rejected"
                rec.declaration_rejection_reason = (
                    info.get("rejection_reason") or "rejected"
                )
                summary["rejected"] += 1
            elif new_status == "amended" and rec.declaration_status != "amended":
                rec.declaration_status = "amended"
                summary["amended"] += 1
            else:
                summary["unchanged"] += 1
        except Exception as exc:
            log.exception("dds_poll_record_error", record_id=str(rec.id), error=str(exc))
            summary["errors"] += 1

    await db.commit()
    log.info("dds_poll_complete", **summary)
    return summary


async def run_polling_loop(interval_seconds: int = POLL_INTERVAL_SECONDS_DEFAULT) -> None:
    """Background loop: run poll_once every `interval_seconds`."""
    from app.db.session import get_session_factory

    factory = get_session_factory()
    while True:
        try:
            async with factory() as db:
                await poll_once(db)
        except Exception:
            log.exception("dds_poll_loop_error")
        await asyncio.sleep(interval_seconds)
