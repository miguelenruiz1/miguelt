"""Pydantic schemas for plan enforcement and usage tracking."""
from __future__ import annotations

from pydantic import BaseModel


class UsageItem(BaseModel):
    current: int
    limit: int
    percentage: float


class UsageSummary(BaseModel):
    plan_name: str
    plan_slug: str
    users: UsageItem
    assets_this_month: UsageItem
    wallets: UsageItem
    subscription_status: str
