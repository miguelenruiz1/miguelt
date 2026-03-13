"""Initial schema: plans, subscriptions, invoices, license_keys, subscription_events

Revision ID: 001
Revises:
Create Date: 2026-02-23
"""
from __future__ import annotations

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Store enum-like columns as plain VARCHAR — no PG native ENUM types.
# This avoids CREATE TYPE conflicts across re-runs and is fully compatible
# with SQLAlchemy's Python-level Enum validation (native_enum=False in models).
_STATUS50 = sa.String(50)


def upgrade() -> None:
    # ── plans ──────────────────────────────────────────────────────────────────
    op.create_table(
        "plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("price_monthly", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("price_annual", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("max_users", sa.Integer, nullable=False, server_default="3"),
        sa.Column("max_assets", sa.Integer, nullable=False, server_default="100"),
        sa.Column("max_wallets", sa.Integer, nullable=False, server_default="5"),
        sa.Column("modules", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("features", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── subscriptions ─────────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False, unique=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", _STATUS50, nullable=False, server_default="active"),
        sa.Column("billing_cycle", _STATUS50, nullable=False, server_default="monthly"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])

    # ── invoices ──────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subscription_id", sa.String(36), sa.ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("invoice_number", sa.String(50), nullable=False, unique=True),
        sa.Column("status", _STATUS50, nullable=False, server_default="open"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("line_items", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_invoices_subscription_id", "invoices", ["subscription_id"])
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_created_at", "invoices", ["created_at"])

    # ── license_keys ──────────────────────────────────────────────────────────
    op.create_table(
        "license_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("subscription_id", sa.String(36), sa.ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", _STATUS50, nullable=False, server_default="active"),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_activations", sa.Integer, nullable=False, server_default="-1"),
        sa.Column("activations_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("features", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_license_keys_tenant_id", "license_keys", ["tenant_id"])
    op.create_index("ix_license_keys_status", "license_keys", ["status"])

    # ── subscription_events ───────────────────────────────────────────────────
    op.create_table(
        "subscription_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subscription_id", sa.String(36), sa.ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("event_type", _STATUS50, nullable=False),
        sa.Column("data", postgresql.JSONB, nullable=True),
        sa.Column("performed_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sub_events_subscription_id", "subscription_events", ["subscription_id"])
    op.create_index("ix_sub_events_tenant_id", "subscription_events", ["tenant_id"])
    op.create_index("ix_sub_events_created_at", "subscription_events", ["created_at"])

    # ── seed plans ────────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    plans = [
        {
            "id": str(uuid.uuid4()),
            "name": "Free",
            "slug": "free",
            "description": "Plan gratuito para equipos pequeños",
            "price_monthly": "0",
            "price_annual": None,
            "currency": "USD",
            "max_users": 3,
            "max_assets": 100,
            "max_wallets": 5,
            "modules": ["assets", "wallets"],
            "features": {},
            "is_active": True,
            "is_archived": False,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Starter",
            "slug": "starter",
            "description": "Para equipos en crecimiento",
            "price_monthly": "49",
            "price_annual": "470",
            "currency": "USD",
            "max_users": 15,
            "max_assets": 2000,
            "max_wallets": 20,
            "modules": ["assets", "wallets", "audit"],
            "features": {"support_level": "email"},
            "is_active": True,
            "is_archived": False,
            "sort_order": 1,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Professional",
            "slug": "professional",
            "description": "Para empresas medianas con analíticas avanzadas",
            "price_monthly": "149",
            "price_annual": "1430",
            "currency": "USD",
            "max_users": 50,
            "max_assets": 20000,
            "max_wallets": 100,
            "modules": ["assets", "wallets", "audit", "analytics"],
            "features": {"support_level": "priority", "api_rate_limit": 10000},
            "is_active": True,
            "is_archived": False,
            "sort_order": 2,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Enterprise",
            "slug": "enterprise",
            "description": "Solución personalizada para grandes organizaciones",
            "price_monthly": "-1",
            "price_annual": None,
            "currency": "USD",
            "max_users": -1,
            "max_assets": -1,
            "max_wallets": -1,
            "modules": ["assets", "wallets", "audit", "analytics", "api", "sso", "custom"],
            "features": {"support_level": "dedicated", "api_rate_limit": -1, "sso": True},
            "is_active": True,
            "is_archived": False,
            "sort_order": 3,
            "created_at": now,
            "updated_at": now,
        },
    ]

    plan_table = sa.table(
        "plans",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("description", sa.Text),
        sa.column("price_monthly", sa.Numeric),
        sa.column("price_annual", sa.Numeric),
        sa.column("currency", sa.String),
        sa.column("max_users", sa.Integer),
        sa.column("max_assets", sa.Integer),
        sa.column("max_wallets", sa.Integer),
        sa.column("modules", postgresql.JSONB),
        sa.column("features", postgresql.JSONB),
        sa.column("is_active", sa.Boolean),
        sa.column("is_archived", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(plan_table, plans)


def downgrade() -> None:
    op.drop_table("subscription_events")
    op.drop_table("license_keys")
    op.drop_table("invoices")
    op.drop_table("subscriptions")
    op.drop_table("plans")
