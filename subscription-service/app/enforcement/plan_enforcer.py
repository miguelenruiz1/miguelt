"""Plan limit enforcement — checks resource usage against plan limits."""
from __future__ import annotations

import httpx
import structlog

from app.core.errors import PlanLimitError
from app.core.settings import get_settings
from app.db.models import Plan, Subscription, SubscriptionStatus
from app.enforcement.schemas import UsageItem, UsageSummary
from app.repositories.plan_repo import PlanRepository
from app.repositories.subscription_repo import SubscriptionRepository

from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


class PlanEnforcer:
    """Enforces plan limits by counting resources across services."""

    def __init__(self, db: AsyncSession, http_client: httpx.AsyncClient) -> None:
        self.db = db
        self.http_client = http_client
        self.sub_repo = SubscriptionRepository(db)
        self.plan_repo = PlanRepository(db)
        self.settings = get_settings()

    # ─── Public checks ─────────────────────────────────────────────────────

    async def check_can_create_user(self, tenant_id: str) -> None:
        """Raise PlanLimitError if user creation would exceed plan limit."""
        sub, plan = await self._get_active_subscription(tenant_id)
        limit = plan.max_users
        if limit == -1:
            return
        current = await self._count_users(tenant_id)
        if current >= limit:
            raise PlanLimitError(
                detail="User limit reached for current plan",
                resource="users",
                current=current,
                limit=limit,
                upgrade_message=f"Your {plan.name} plan allows {limit} users. Upgrade to add more.",
            )

    async def check_can_create_asset(self, tenant_id: str) -> None:
        """Raise PlanLimitError if asset creation this month would exceed plan limit."""
        sub, plan = await self._get_active_subscription(tenant_id)
        limit = plan.max_assets
        if limit == -1:
            return
        current = await self._count_assets_this_month(tenant_id)
        if current >= limit:
            raise PlanLimitError(
                detail="Monthly asset limit reached for current plan",
                resource="assets",
                current=current,
                limit=limit,
                upgrade_message=f"Your {plan.name} plan allows {limit} assets/month. Upgrade to add more.",
            )

    async def check_can_create_wallet(self, tenant_id: str) -> None:
        """Raise PlanLimitError if wallet creation would exceed plan limit."""
        sub, plan = await self._get_active_subscription(tenant_id)
        limit = plan.max_wallets
        if limit == -1:
            return
        current = await self._count_wallets(tenant_id)
        if current >= limit:
            raise PlanLimitError(
                detail="Wallet limit reached for current plan",
                resource="wallets",
                current=current,
                limit=limit,
                upgrade_message=f"Your {plan.name} plan allows {limit} wallets. Upgrade to add more.",
            )

    async def get_usage_summary(self, tenant_id: str) -> UsageSummary:
        """Return full usage summary for the tenant's current plan."""
        sub = await self.sub_repo.get_by_tenant(tenant_id)
        if not sub or not sub.plan:
            return UsageSummary(
                plan_name="No Plan",
                plan_slug="none",
                users=UsageItem(current=0, limit=0, percentage=0.0),
                assets_this_month=UsageItem(current=0, limit=0, percentage=0.0),
                wallets=UsageItem(current=0, limit=0, percentage=0.0),
                subscription_status="none",
            )

        plan = sub.plan
        users_count = await self._count_users(tenant_id)
        assets_count = await self._count_assets_this_month(tenant_id)
        wallets_count = await self._count_wallets(tenant_id)

        return UsageSummary(
            plan_name=plan.name,
            plan_slug=plan.slug,
            users=self._build_usage_item(users_count, plan.max_users),
            assets_this_month=self._build_usage_item(assets_count, plan.max_assets),
            wallets=self._build_usage_item(wallets_count, plan.max_wallets),
            subscription_status=sub.status.value if sub.status else "none",
        )

    # ─── Internal helpers ──────────────────────────────────────────────────

    async def _get_active_subscription(self, tenant_id: str) -> tuple[Subscription, Plan]:
        """Get active subscription + plan, or raise PlanLimitError if expired/canceled."""
        sub = await self.sub_repo.get_by_tenant(tenant_id)
        if not sub:
            raise PlanLimitError(
                detail="No active subscription found",
                resource="subscription",
                current=0,
                limit=0,
                upgrade_message="No active subscription. Please subscribe to a plan.",
            )

        if sub.status in (SubscriptionStatus.expired, SubscriptionStatus.canceled):
            raise PlanLimitError(
                detail=f"Subscription is {sub.status.value}",
                resource="subscription",
                current=0,
                limit=0,
                upgrade_message="Your subscription is no longer active. Please renew or reactivate.",
            )

        if not sub.plan:
            raise PlanLimitError(
                detail="Subscription has no associated plan",
                resource="subscription",
                current=0,
                limit=0,
                upgrade_message="Subscription configuration error. Contact support.",
            )

        return sub, sub.plan

    async def _count_users(self, tenant_id: str) -> int:
        """Count users via HTTP call to user-service."""
        try:
            resp = await self.http_client.get(
                f"{self.settings.USER_SERVICE_URL}/api/v1/users",
                headers={"X-Tenant-Id": tenant_id},
                params={"limit": 1, "offset": 0},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("total", 0)
        except httpx.RequestError as exc:
            log.warning("user_service_unreachable", tenant_id=tenant_id, error=str(exc))
        return 0

    async def _count_assets_this_month(self, tenant_id: str) -> int:
        """Count assets created this month via HTTP call to trace-service."""
        try:
            resp = await self.http_client.get(
                f"http://trace-api:8000/api/v1/assets",
                headers={"X-Tenant-Id": tenant_id},
                params={"limit": 1, "offset": 0, "this_month": "true"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("total", 0)
        except httpx.RequestError as exc:
            log.warning("trace_service_unreachable", tenant_id=tenant_id, error=str(exc))
        return 0

    async def _count_wallets(self, tenant_id: str) -> int:
        """Count wallets via HTTP call to trace-service."""
        try:
            resp = await self.http_client.get(
                f"http://trace-api:8000/api/v1/registry/wallets",
                headers={"X-Tenant-Id": tenant_id},
                params={"limit": 1, "offset": 0},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("total", 0)
        except httpx.RequestError as exc:
            log.warning("trace_service_unreachable", tenant_id=tenant_id, error=str(exc))
        return 0

    @staticmethod
    def _build_usage_item(current: int, limit: int) -> UsageItem:
        if limit == -1:
            return UsageItem(current=current, limit=-1, percentage=0.0)
        pct = (current / limit * 100) if limit > 0 else 0.0
        return UsageItem(current=current, limit=limit, percentage=round(pct, 1))
