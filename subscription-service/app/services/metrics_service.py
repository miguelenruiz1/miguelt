"""Metrics and overview statistics for the subscription dashboard."""
from __future__ import annotations

from datetime import datetime, timezone
from calendar import monthrange

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Subscription, SubscriptionStatus
from app.repositories.subscription_repo import SubscriptionRepository


class MetricsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SubscriptionRepository(db)

    async def get_overview(self) -> dict:
        # Counts by status
        counts = await self.repo.count_by_status()

        active  = counts.get(SubscriptionStatus.active, 0)
        trialing = counts.get(SubscriptionStatus.trialing, 0)
        past_due = counts.get(SubscriptionStatus.past_due, 0)
        canceled = counts.get(SubscriptionStatus.canceled, 0)
        expired  = counts.get(SubscriptionStatus.expired, 0)

        # MRR breakdown by plan
        plan_breakdown = await self.repo.mrr_by_plan()
        mrr = sum(r["mrr"] for r in plan_breakdown)
        arr = mrr * 12

        # New this month
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_this_month_result = await self.db.execute(
            select(func.count(Subscription.id))
            .where(Subscription.created_at >= month_start)
        )
        new_this_month = new_this_month_result.scalar_one()

        # Canceled this month
        canceled_this_month_result = await self.db.execute(
            select(func.count(Subscription.id))
            .where(
                Subscription.canceled_at >= month_start,
                Subscription.status == SubscriptionStatus.canceled,
            )
        )
        canceled_this_month = canceled_this_month_result.scalar_one()

        return {
            "mrr": round(mrr, 2),
            "arr": round(arr, 2),
            "active": active,
            "trialing": trialing,
            "past_due": past_due,
            "canceled": canceled,
            "expired": expired,
            "new_this_month": new_this_month,
            "canceled_this_month": canceled_this_month,
            "plan_breakdown": plan_breakdown,
        }
