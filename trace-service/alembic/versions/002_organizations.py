"""organizations and taxonomy

Revision ID: 002_organizations
Revises: 001_initial
Create Date: 2026-02-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID

revision: str = "002_organizations"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── custodian_types ──────────────────────────────────────────────────────
    op.create_table(
        "custodian_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=False, server_default="#6366f1"),
        sa.Column("icon", sa.Text(), nullable=False, server_default="building"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint(
        "uq_custodian_types_slug", "custodian_types", ["slug"]
    )

    # ─── organizations ────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "custodian_type_id",
            UUID(as_uuid=True),
            sa.ForeignKey("custodian_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "tags",
            ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_organizations_type", "organizations", ["custodian_type_id"])
    op.create_index("ix_organizations_status", "organizations", ["status"])

    # ─── registry_wallets: add name + organization_id ─────────────────────────
    op.add_column("registry_wallets", sa.Column("name", sa.Text(), nullable=True))
    op.add_column(
        "registry_wallets",
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_registry_wallets_org", "registry_wallets", ["organization_id"]
    )

    # ─── Seed default custodian types ─────────────────────────────────────────
    op.execute(
        """
        INSERT INTO custodian_types (id, name, slug, color, icon, sort_order, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'Farm',      'farm',      '#16a34a', 'sprout',   0, now(), now()),
            (gen_random_uuid(), 'Warehouse', 'warehouse', '#2563eb', 'warehouse',1, now(), now()),
            (gen_random_uuid(), 'Truck',     'truck',     '#d97706', 'truck',    2, now(), now()),
            (gen_random_uuid(), 'Customs',   'customs',   '#9333ea', 'shield',   3, now(), now())
        """
    )


def downgrade() -> None:
    op.drop_index("ix_registry_wallets_org", "registry_wallets")
    op.drop_column("registry_wallets", "organization_id")
    op.drop_column("registry_wallets", "name")
    op.drop_table("organizations")
    op.drop_table("custodian_types")
