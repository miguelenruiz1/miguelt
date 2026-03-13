"""multi-tenancy + cNFT blockchain fields

Revision ID: 003_multi_tenant
Revises: 002_organizations
Create Date: 2026-02-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

revision: str = "003_multi_tenant"
down_revision: Union[str, None] = "002_organizations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # ─── 1. Create tenants table ───────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
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
    op.create_unique_constraint("uq_tenants_slug", "tenants", ["slug"])

    # ─── 2. Insert default tenant ──────────────────────────────────────────────
    op.execute(
        f"""
        INSERT INTO tenants (id, name, slug, status, metadata, created_at, updated_at)
        VALUES (
            '{DEFAULT_TENANT_ID}',
            'Default',
            'default',
            'active',
            '{{}}',
            now(),
            now()
        )
        """
    )

    # ─── 3. Create tenant_merkle_trees table ───────────────────────────────────
    op.create_table(
        "tenant_merkle_trees",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("tree_address", sa.Text(), nullable=False),
        sa.Column("tree_authority", sa.Text(), nullable=False),
        sa.Column("max_depth", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("max_buffer_size", sa.Integer(), nullable=False, server_default="64"),
        sa.Column("canopy_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leaf_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("helius_tree_id", sa.Text(), nullable=True),
        sa.Column("create_tx_sig", sa.Text(), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default="false"),
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

    # ─── 4. Add tenant_id to existing tables (with server_default for existing rows) ──

    # custodian_types
    op.add_column(
        "custodian_types",
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=DEFAULT_TENANT_ID,
        ),
    )

    # organizations
    op.add_column(
        "organizations",
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=DEFAULT_TENANT_ID,
        ),
    )

    # registry_wallets
    op.add_column(
        "registry_wallets",
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=DEFAULT_TENANT_ID,
        ),
    )

    # assets
    op.add_column(
        "assets",
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            server_default=DEFAULT_TENANT_ID,
        ),
    )

    # ─── 5. Fix unique constraint on custodian_types ───────────────────────────
    op.drop_constraint("uq_custodian_types_slug", "custodian_types", type_="unique")
    op.create_unique_constraint(
        "uq_custodian_types_slug_tenant", "custodian_types", ["slug", "tenant_id"]
    )

    # ─── 6. Add blockchain / cNFT columns to assets ───────────────────────────
    op.add_column("assets", sa.Column("blockchain_asset_id", sa.Text(), nullable=True))
    op.add_column("assets", sa.Column("blockchain_tree_address", sa.Text(), nullable=True))
    op.add_column("assets", sa.Column("blockchain_tx_signature", sa.Text(), nullable=True))
    op.add_column(
        "assets",
        sa.Column(
            "blockchain_status",
            sa.Text(),
            nullable=False,
            server_default="SKIPPED",
        ),
    )
    op.add_column(
        "assets",
        sa.Column(
            "is_compressed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # ─── 7. Create indexes ─────────────────────────────────────────────────────
    op.create_index("ix_organizations_tenant", "organizations", ["tenant_id"])
    op.create_index("ix_assets_tenant", "assets", ["tenant_id"])
    op.create_index("ix_registry_wallets_tenant", "registry_wallets", ["tenant_id"])

    # ─── 8. Remove server_default from tenant_id columns ──────────────────────
    # (force future inserts to always provide an explicit tenant_id)
    op.alter_column("custodian_types", "tenant_id", server_default=None)
    op.alter_column("organizations", "tenant_id", server_default=None)
    op.alter_column("registry_wallets", "tenant_id", server_default=None)
    op.alter_column("assets", "tenant_id", server_default=None)


def downgrade() -> None:
    # Blockchain fields
    op.drop_column("assets", "is_compressed")
    op.drop_column("assets", "blockchain_status")
    op.drop_column("assets", "blockchain_tx_signature")
    op.drop_column("assets", "blockchain_tree_address")
    op.drop_column("assets", "blockchain_asset_id")

    # Indexes
    op.drop_index("ix_registry_wallets_tenant", "registry_wallets")
    op.drop_index("ix_assets_tenant", "assets")
    op.drop_index("ix_organizations_tenant", "organizations")

    # Restore old unique constraint on custodian_types
    op.drop_constraint("uq_custodian_types_slug_tenant", "custodian_types", type_="unique")
    op.create_unique_constraint("uq_custodian_types_slug", "custodian_types", ["slug"])

    # Drop tenant_id columns
    op.drop_column("assets", "tenant_id")
    op.drop_column("registry_wallets", "tenant_id")
    op.drop_column("organizations", "tenant_id")
    op.drop_column("custodian_types", "tenant_id")

    # Drop new tables
    op.drop_table("tenant_merkle_trees")
    op.drop_table("tenants")
