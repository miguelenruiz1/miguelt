"""Initial schema: users, roles, permissions, audit_logs

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

# ─── 26 permissions to seed ───────────────────────────────────────────────────
PERMISSIONS = [
    # module, slug, name
    ("users",         "users.view",                  "View users"),
    ("users",         "users.create",                "Create users"),
    ("users",         "users.edit",                  "Edit users"),
    ("users",         "users.delete",                "Delete users"),
    ("roles",         "roles.view",                  "View roles"),
    ("roles",         "roles.create",                "Create roles"),
    ("roles",         "roles.edit",                  "Edit roles"),
    ("roles",         "roles.delete",                "Delete roles"),
    ("roles",         "roles.assign_permissions",    "Assign permissions to roles"),
    ("assets",        "assets.view",                 "View assets"),
    ("assets",        "assets.create",               "Create assets"),
    ("assets",        "assets.mint",                 "Mint NFT assets"),
    ("assets",        "assets.handoff",              "Handoff assets"),
    ("assets",        "assets.qc",                   "QC inspect assets"),
    ("assets",        "assets.release",              "Release assets"),
    ("assets",        "assets.burn",                 "Burn assets"),
    ("wallets",       "wallets.view",                "View wallets"),
    ("wallets",       "wallets.create",              "Create wallets"),
    ("wallets",       "wallets.edit",                "Edit wallets"),
    ("organizations", "organizations.view",          "View organizations"),
    ("organizations", "organizations.create",        "Create organizations"),
    ("organizations", "organizations.edit",          "Edit organizations"),
    ("organizations", "organizations.delete",        "Delete organizations"),
    ("audit",         "audit.view",                  "View audit logs"),
    ("system",        "system.view",                 "View system info"),
    ("system",        "system.admin",                "System administration"),
]


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ── roles ──────────────────────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("slug", "tenant_id", name="uq_roles_slug_tenant"),
    )

    # ── permissions ────────────────────────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("module", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_permissions_module", "permissions", ["module"])

    # ── user_roles ─────────────────────────────────────────────────────────
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles"),
    )

    # ── role_permissions ───────────────────────────────────────────────────
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions"),
    )

    # ── audit_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── seed permissions ───────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    perm_rows = [
        {"id": str(uuid.uuid4()), "module": m, "slug": s, "name": n, "created_at": now}
        for m, s, n in PERMISSIONS
    ]
    op.bulk_insert(
        sa.table(
            "permissions",
            sa.column("id", sa.String),
            sa.column("module", sa.String),
            sa.column("slug", sa.String),
            sa.column("name", sa.String),
            sa.column("created_at", sa.DateTime(timezone=True)),
        ),
        perm_rows,
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
