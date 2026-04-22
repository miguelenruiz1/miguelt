"""Pydantic schemas for subscription-service API."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import BillingCycle, EventType, InvoiceStatus, LicenseStatus, SubscriptionStatus

T = TypeVar("T")


# ─── Generic Pagination ───────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int


# ─── Plan ─────────────────────────────────────────────────────────────────────

class PlanSlim(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    price_monthly: Decimal
    currency: str
    max_users: int
    max_assets: int
    max_wallets: int


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: str | None
    price_monthly: Decimal
    price_annual: Decimal | None
    currency: str
    max_users: int
    max_assets: int
    max_wallets: int
    modules: list[Any]
    features: dict[str, Any]
    is_active: bool
    is_archived: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    price_monthly: Decimal = Field(default=Decimal("0"))
    price_annual: Decimal | None = None
    currency: str = Field(default="USD", max_length=3)
    max_users: int = Field(default=3)
    max_assets: int = Field(default=100)
    max_wallets: int = Field(default=5)
    modules: list[str] = Field(default_factory=list)
    features: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    sort_order: int = 0


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price_monthly: Decimal | None = None
    price_annual: Decimal | None = None
    currency: str | None = None
    max_users: int | None = None
    max_assets: int | None = None
    max_wallets: int | None = None
    modules: list[str] | None = None
    features: dict[str, Any] | None = None
    is_active: bool | None = None
    sort_order: int | None = None


# ─── Subscription ─────────────────────────────────────────────────────────────

class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    plan: PlanSlim
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    current_period_start: datetime
    current_period_end: datetime
    trial_ends_at: datetime | None
    canceled_at: datetime | None
    cancellation_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class SubscriptionCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    plan_slug: str = Field(default="free")
    billing_cycle: BillingCycle = BillingCycle.monthly
    notes: str | None = None


class CancelRequest(BaseModel):
    reason: str | None = None


class UpgradeRequest(BaseModel):
    plan_slug: str


# ─── Invoice ──────────────────────────────────────────────────────────────────

class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subscription_id: str
    tenant_id: str
    invoice_number: str
    status: InvoiceStatus
    amount: Decimal
    currency: str
    period_start: datetime
    period_end: datetime
    due_date: date | None
    paid_at: datetime | None
    line_items: list[Any]
    gateway_tx_id: str | None = None
    gateway_slug: str | None = None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class MarkPaidRequest(BaseModel):
    notes: str | None = None


# ─── License ──────────────────────────────────────────────────────────────────

class LicenseKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    tenant_id: str
    subscription_id: str | None
    status: LicenseStatus
    issued_at: datetime
    expires_at: datetime | None
    max_activations: int
    activations_count: int
    features: list[Any]
    notes: str | None
    revoked_at: datetime | None
    revoked_by: str | None
    created_at: datetime
    updated_at: datetime


class IssueKeyRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    subscription_id: str | None = None
    expires_at: datetime | None = None
    max_activations: int = Field(default=-1)
    features: list[str] = Field(default_factory=list)
    notes: str | None = None


# ─── Events ───────────────────────────────────────────────────────────────────

class SubscriptionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subscription_id: str
    tenant_id: str
    event_type: EventType
    data: dict[str, Any] | None
    performed_by: str | None
    created_at: datetime


# ─── Metrics ──────────────────────────────────────────────────────────────────

class PlanBreakdownItem(BaseModel):
    slug: str
    name: str
    price_monthly: float
    count: int
    mrr: float


class OverviewMetrics(BaseModel):
    mrr: float
    arr: float
    active: int
    trialing: int
    past_due: int
    canceled: int
    expired: int
    new_this_month: int
    canceled_this_month: int
    plan_breakdown: list[PlanBreakdownItem]


# ─── Payment Gateways ─────────────────────────────────────────────────────────

class GatewayField(BaseModel):
    key: str
    label: str
    type: str       # "text" | "password"
    required: bool


class GatewayCatalogItem(BaseModel):
    slug: str
    name: str
    description: str
    color: str
    fields: list[GatewayField]


class GatewayConfigSave(BaseModel):
    credentials: dict[str, str] = Field(default_factory=dict)


class GatewayConfigOut(BaseModel):
    slug: str
    display_name: str
    is_active: bool
    configured: bool
    credentials_masked: dict[str, str]
    updated_at: datetime | None
