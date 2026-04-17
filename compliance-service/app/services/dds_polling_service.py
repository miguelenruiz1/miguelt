"""Background polling loop for DDS validation status.

Scans compliance_records with declaration_status='submitted' at regular
intervals and calls TRACES NT retrieveDdsInfoByReferences to pick up the
EU-side verdict. On the first transition to 'validated' we also notify the
operator (buyer) by email.

Isolated from the request path so latency spikes in TRACES NT don't affect
user-facing calls; runs inside the compliance-service lifespan as a task.

Distributed-safe: before each pass the loop tries to grab a short-lived
Redis lock (dds:poll:leader). Whichever replica wins runs the pass; the
others sleep through the interval. Without this, N replicas would fire
duplicate SOAP calls and — on transition to validated — duplicate emails.
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

# Leader election: lock TTL is slightly shorter than the poll interval so a
# crashed leader can't hold the lock indefinitely — the next tick re-elects.
POLL_LOCK_KEY = "dds:poll:leader"
POLL_LOCK_TTL_SECONDS = POLL_INTERVAL_SECONDS_DEFAULT - 5

# Email idempotency: once we've emailed about a given reference, skip for a
# year (EUDR retains DDS records for 5y, but re-notifying annually is the
# right balance between safety and noise). Key: dds:notified:<ref>.
NOTIFY_GUARD_TTL_SECONDS = 60 * 60 * 24 * 365

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
    """Send the 'DDS validated' email to the operator (buyer).

    Gated by a Redis SETNX so two replicas (or a race between poll passes)
    can't both hit the transition and spam the customer.
    """
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

    reference = record.declaration_reference or str(record.id)
    try:
        from app.api.deps import get_redis
        rd = await get_redis()
        claimed = await rd.set(
            f"dds:notified:{reference}",
            "1",
            nx=True,
            ex=NOTIFY_GUARD_TTL_SECONDS,
        )
        if not claimed:
            log.info(
                "dds_validated_notify_skipped_duplicate",
                record_id=str(record.id),
                reference=reference,
            )
            return
    except Exception as exc:
        # Redis down: degrade to fire — better one extra email than silent skip.
        log.warning("dds_notify_guard_error", error=str(exc), reference=reference)

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
    # Collect records that transitioned to VALIDATED so we can email AFTER
    # the DB commit succeeds. Sending email inside the loop (before commit)
    # risks the operator getting a "validated" notice while the row rolls
    # back and stays "submitted", so we'd re-notify on the next pass.
    newly_validated: list[ComplianceRecord] = []

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
                newly_validated.append(rec)
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

    # Post-commit: now it's safe to notify. Any email failure is logged but
    # does not roll back the DB state (which is already durable).
    for rec in newly_validated:
        try:
            await _notify_validated(rec)
        except Exception:
            log.exception("dds_validated_notify_error", record_id=str(rec.id))

    log.info("dds_poll_complete", **summary)
    return summary


async def run_polling_loop(interval_seconds: int = POLL_INTERVAL_SECONDS_DEFAULT) -> None:
    """Background loop: run poll_once every `interval_seconds`.

    Only the replica that wins the Redis leader lock runs a pass; the rest
    sleep. Lock TTL is slightly below the interval so a crashed leader
    releases the lock naturally within one tick.
    """
    from app.api.deps import get_redis
    from app.db.session import get_session_factory

    factory = get_session_factory()
    lock_ttl = max(10, interval_seconds - 5)
    while True:
        leader = False
        try:
            rd = await get_redis()
            leader = bool(await rd.set(POLL_LOCK_KEY, "1", nx=True, ex=lock_ttl))
        except Exception as exc:
            # Redis unavailable: run anyway — duplicate work is preferable to
            # skipping polling entirely, and single-replica dev always wins.
            log.warning("dds_poll_lock_error", error=str(exc))
            leader = True

        if leader:
            try:
                async with factory() as db:
                    await poll_once(db)
            except Exception:
                log.exception("dds_poll_loop_error")
        await asyncio.sleep(interval_seconds)
