"""ORM models for subscription-service."""
from __future__ import annotations

import enum
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index,
    Integer, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy import Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class SubscriptionStatus(str, enum.Enum):
    active      = "active"
    trialing    = "trialing"
    past_due    = "past_due"
    canceled    = "canceled"
    expired     = "expired"


class BillingCycle(str, enum.Enum):
    monthly = "monthly"
    annual  = "annual"
    custom  = "custom"


class InvoiceStatus(str, enum.Enum):
    draft          = "draft"
    open           = "open"
    paid           = "paid"
    void           = "void"
    uncollectible  = "uncollectible"


class LicenseStatus(str, enum.Enum):
    active  = "active"
    revoked = "revoked"
    expired = "expired"


class EventType(str, enum.Enum):
    created           = "created"
    plan_changed      = "plan_changed"
    canceled          = "canceled"
    reactivated       = "reactivated"
    invoice_generated = "invoice_generated"
    payment_received  = "payment_received"
    trial_started     = "trial_started"
    trial_ended       = "trial_ended"
    status_change     = "status_change"
    expired           = "expired"


# ─── Plan ─────────────────────────────────────────────────────────────────────

class Plan(Base):
    __tablename__ = "plans"

    id:            Mapped[str] = mapped_column(String(36), primary_key=True)
    name:          Mapped[str] = mapped_column(String(100), nullable=False)
    slug:          Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description:   Mapped[str | None] = mapped_column(Text, nullable=True)
    price_monthly: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default="0")
    price_annual:  Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency:      Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    max_users:     Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    max_assets:    Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    max_wallets:   Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    modules:       Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    features:      Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    is_active:     Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_archived:   Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order:    Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at:    Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    subscriptions: Mapped[list[Subscription]] = relationship("Subscription", back_populates="plan")


# ─── Subscription ─────────────────────────────────────────────────────────────

class Subscription(Base):
    __tablename__ = "subscriptions"

    id:                   Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id:            Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    plan_id:              Mapped[str] = mapped_column(String(36), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    status:               Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus, native_enum=False), nullable=False, server_default="active")
    billing_cycle:        Mapped[BillingCycle] = mapped_column(Enum(BillingCycle, native_enum=False), nullable=False, server_default="monthly")
    current_period_start: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end:   Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    trial_ends_at:        Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at:          Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason:  Mapped[str | None] = mapped_column(Text, nullable=True)
    notes:                Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at:           Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:           Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    plan:     Mapped[Plan] = relationship("Plan", back_populates="subscriptions")
    invoices: Mapped[list[Invoice]] = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")
    licenses: Mapped[list[LicenseKey]] = relationship("LicenseKey", back_populates="subscription")
    events:   Mapped[list[SubscriptionEvent]] = relationship("SubscriptionEvent", back_populates="subscription", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_subscriptions_tenant_id", "tenant_id"),
        Index("ix_subscriptions_status", "status"),
        Index("ix_subscriptions_plan_id", "plan_id"),
    )


# ─── Invoice ──────────────────────────────────────────────────────────────────

class Invoice(Base):
    __tablename__ = "invoices"

    id:              Mapped[str] = mapped_column(String(36), primary_key=True)
    subscription_id: Mapped[str] = mapped_column(String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    tenant_id:       Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_number:  Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    status:          Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus, native_enum=False), nullable=False, server_default="open")
    amount:          Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency:        Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    period_start:    Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end:      Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date:        Mapped[Date | None] = mapped_column(Date, nullable=True)
    paid_at:         Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    line_items:      Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    gateway_tx_id:   Mapped[str | None] = mapped_column(String(255), nullable=True)
    gateway_slug:    Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes:           Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at:      Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:      Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    subscription: Mapped[Subscription] = relationship("Subscription", back_populates="invoices")

    __table_args__ = (
        Index("ix_invoices_subscription_id", "subscription_id"),
        Index("ix_invoices_tenant_id", "tenant_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_created_at", "created_at"),
        Index("ix_invoices_gateway_tx_id", "gateway_tx_id"),
    )


# ─── LicenseKey ───────────────────────────────────────────────────────────────

class LicenseKey(Base):
    __tablename__ = "license_keys"

    id:                Mapped[str] = mapped_column(String(36), primary_key=True)
    key:               Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    tenant_id:         Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_id:   Mapped[str | None] = mapped_column(String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    status:            Mapped[LicenseStatus] = mapped_column(Enum(LicenseStatus, native_enum=False), nullable=False, server_default="active")
    issued_at:         Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at:        Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_activations:   Mapped[int] = mapped_column(Integer, nullable=False, server_default="-1")
    activations_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    features:          Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    notes:             Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_at:        Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by:        Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:        Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:        Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    subscription: Mapped[Subscription | None] = relationship("Subscription", back_populates="licenses")

    __table_args__ = (
        Index("ix_license_keys_tenant_id", "tenant_id"),
        Index("ix_license_keys_status", "status"),
    )


# ─── SubscriptionEvent ────────────────────────────────────────────────────────

class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    id:              Mapped[str] = mapped_column(String(36), primary_key=True)
    subscription_id: Mapped[str] = mapped_column(String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    tenant_id:       Mapped[str] = mapped_column(String(255), nullable=False)
    event_type:      Mapped[EventType] = mapped_column(Enum(EventType, native_enum=False), nullable=False)
    data:            Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    performed_by:    Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:      Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscription: Mapped[Subscription] = relationship("Subscription", back_populates="events")

    __table_args__ = (
        Index("ix_sub_events_subscription_id", "subscription_id"),
        Index("ix_sub_events_tenant_id", "tenant_id"),
        Index("ix_sub_events_created_at", "created_at"),
    )


# ─── TenantModuleActivation ───────────────────────────────────────────────────

class TenantModuleActivation(Base):
    __tablename__ = "tenant_module_activations"

    id:              Mapped[str]           = mapped_column(String(36), primary_key=True)
    tenant_id:       Mapped[str]           = mapped_column(String(255), nullable=False)
    module_slug:     Mapped[str]           = mapped_column(String(50), nullable=False)
    is_active:       Mapped[bool]          = mapped_column(Boolean, nullable=False, server_default="true")
    activated_at:    Mapped[DateTime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_by:    Mapped[str | None]    = mapped_column(String(255), nullable=True)
    deactivated_at:  Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_by:  Mapped[str | None]    = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "module_slug", name="uq_tenant_module"),
        Index("ix_tenant_module_activations_tenant_id", "tenant_id"),
    )


# ─── PaymentGatewayConfig ─────────────────────────────────────────────────────

class PaymentGatewayConfig(Base):
    __tablename__ = "payment_gateway_configs"

    id:           Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:    Mapped[str]        = mapped_column(String(255), nullable=False)
    gateway_slug: Mapped[str]        = mapped_column(String(50), nullable=False)
    display_name: Mapped[str]        = mapped_column(String(100), nullable=False)
    is_active:    Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    is_test_mode: Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    credentials:  Mapped[dict]       = mapped_column(JSONB, nullable=False, server_default="{}")
    extra_config: Mapped[dict]       = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at:   Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "gateway_slug", name="uq_tenant_gateway"),
        Index("ix_payment_gateway_configs_tenant_id", "tenant_id"),
    )


# ─── Platform AI Settings (singleton) ────────────────────────────────────────

class PlatformAISettings(Base):
    __tablename__ = "platform_ai_settings"

    id:                              Mapped[str]   = mapped_column(String(36), primary_key=True)
    created_at:                      Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:                      Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # Anthropic
    anthropic_api_key_encrypted:     Mapped[str | None] = mapped_column(Text, nullable=True)
    anthropic_model_analysis:        Mapped[str]   = mapped_column(String(100), nullable=False, server_default="claude-haiku-4-5-20251001")
    anthropic_model_premium:         Mapped[str]   = mapped_column(String(100), nullable=False, server_default="claude-sonnet-4-6")
    anthropic_max_tokens:            Mapped[int]   = mapped_column(Integer, nullable=False, server_default="2048")
    anthropic_enabled:               Mapped[bool]  = mapped_column(Boolean, nullable=False, server_default="false")
    # Limits
    global_daily_limit_free:         Mapped[int]   = mapped_column(Integer, nullable=False, server_default="0")
    global_daily_limit_starter:      Mapped[int]   = mapped_column(Integer, nullable=False, server_default="10")
    global_daily_limit_professional: Mapped[int]   = mapped_column(Integer, nullable=False, server_default="50")
    global_daily_limit_enterprise:   Mapped[int]   = mapped_column(Integer, nullable=False, server_default="-1")
    # Cache
    cache_ttl_minutes:               Mapped[int]   = mapped_column(Integer, nullable=False, server_default="60")
    cache_enabled:                   Mapped[bool]  = mapped_column(Boolean, nullable=False, server_default="true")
    # Cost
    estimated_cost_per_analysis_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, server_default="0.003")
    alert_monthly_cost_usd:          Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default="50.0")
    current_month_calls:             Mapped[int]   = mapped_column(Integer, nullable=False, server_default="0")
    current_month_cost_usd:          Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, server_default="0.0")
    # Features
    pnl_analysis_enabled:            Mapped[bool]  = mapped_column(Boolean, nullable=False, server_default="true")
