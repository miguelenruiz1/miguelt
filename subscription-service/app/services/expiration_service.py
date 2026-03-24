"""Automatic subscription expiration.

Runs periodically to:
1. Mark active/trialing subscriptions as past_due after current_period_end
2. Mark past_due subscriptions as expired after a grace period (configurable)
3. Deactivate modules for expired tenants
4. Log events for each transition
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    EventType,
    Subscription,
    SubscriptionStatus,
)
from app.repositories.event_repo import EventRepository

log = structlog.get_logger(__name__)

# Grace period: days after current_period_end before marking as expired
GRACE_PERIOD_DAYS = 3


async def check_expirations(db: AsyncSession) -> dict:
    """Check all subscriptions and apply status transitions.

    Returns summary of actions taken.
    """
    now = datetime.now(timezone.utc)
    event_repo = EventRepository(db)
    summary = {"past_due": 0, "expired": 0, "deactivated_modules": 0}

    # 1. active/trialing → past_due (period ended, within grace period)
    grace_cutoff = now - timedelta(days=GRACE_PERIOD_DAYS)

    result = await db.execute(
        select(Subscription).where(
            Subscription.status.in_([
                SubscriptionStatus.active,
                SubscriptionStatus.trialing,
            ]),
            Subscription.current_period_end < now,
            Subscription.current_period_end >= grace_cutoff,
        )
    )
    for sub in result.scalars():
        old_status = sub.status.value
        sub.status = SubscriptionStatus.past_due
        summary["past_due"] += 1

        await event_repo.create(
            subscription_id=sub.id,
            tenant_id=sub.tenant_id,
            event_type=EventType.status_change,
            data={
                "from": old_status,
                "to": "past_due",
                "reason": "payment_overdue",
                "period_end": sub.current_period_end.isoformat(),
            },
            performed_by="system:expiration",
        )
        log.info(
            "subscription_past_due",
            tenant_id=sub.tenant_id,
            subscription_id=sub.id,
            period_end=sub.current_period_end.isoformat(),
        )

    # 2. past_due → expired (grace period exceeded)
    result = await db.execute(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.past_due,
            Subscription.current_period_end < grace_cutoff,
        )
    )
    for sub in result.scalars():
        sub.status = SubscriptionStatus.expired
        summary["expired"] += 1

        await event_repo.create(
            subscription_id=sub.id,
            tenant_id=sub.tenant_id,
            event_type=EventType.status_change,
            data={
                "from": "past_due",
                "to": "expired",
                "reason": "grace_period_exceeded",
                "grace_days": GRACE_PERIOD_DAYS,
            },
            performed_by="system:expiration",
        )

        # Deactivate all modules for this tenant
        from app.db.models import TenantModuleActivation
        mod_result = await db.execute(
            select(TenantModuleActivation).where(
                TenantModuleActivation.tenant_id == sub.tenant_id,
                TenantModuleActivation.is_active == True,  # noqa: E712
            )
        )
        for mod in mod_result.scalars():
            mod.is_active = False
            mod.deactivated_at = now
            summary["deactivated_modules"] += 1

        log.warning(
            "subscription_expired",
            tenant_id=sub.tenant_id,
            subscription_id=sub.id,
            modules_deactivated=summary["deactivated_modules"],
        )

    # 3. Also mark active subs that are WAY past due (missed grace window somehow)
    result = await db.execute(
        select(Subscription).where(
            Subscription.status.in_([
                SubscriptionStatus.active,
                SubscriptionStatus.trialing,
            ]),
            Subscription.current_period_end < grace_cutoff,
        )
    )
    for sub in result.scalars():
        sub.status = SubscriptionStatus.expired
        summary["expired"] += 1

        await event_repo.create(
            subscription_id=sub.id,
            tenant_id=sub.tenant_id,
            event_type=EventType.status_change,
            data={
                "from": sub.status.value if hasattr(sub.status, "value") else str(sub.status),
                "to": "expired",
                "reason": "payment_overdue_no_grace",
            },
            performed_by="system:expiration",
        )
        log.warning("subscription_force_expired", tenant_id=sub.tenant_id)

    await db.flush()
    await db.commit()
    return summary


async def run_expiration_loop(interval_seconds: int = 3600):
    """Background loop that checks expirations periodically."""
    from app.db.session import get_db

    log.info("expiration_loop_started", interval=interval_seconds)
    while True:
        try:
            async with get_db() as db:
                summary = await check_expirations(db)
                if summary["past_due"] or summary["expired"]:
                    log.info("expiration_check_complete", **summary)
        except asyncio.CancelledError:
            log.info("expiration_loop_cancelled")
            break
        except Exception as exc:
            log.error("expiration_check_failed", error=str(exc))

        await asyncio.sleep(interval_seconds)
