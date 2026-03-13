"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── registry_wallets ─────────────────────────────────────────────────────
    op.create_table(
        "registry_wallets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_pubkey", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
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
        "uq_registry_wallets_pubkey", "registry_wallets", ["wallet_pubkey"]
    )
    op.create_index("ix_registry_wallets_status", "registry_wallets", ["status"])

    # ─── assets ───────────────────────────────────────────────────────────────
    op.create_table(
        "assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("asset_mint", sa.Text(), nullable=False),
        sa.Column("product_type", sa.Text(), nullable=False),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column("current_custodian_wallet", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("last_event_hash", sa.Text(), nullable=True),
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
    op.create_unique_constraint("uq_assets_mint", "assets", ["asset_mint"])
    op.create_index("ix_assets_product_type", "assets", ["product_type"])
    op.create_index("ix_assets_custodian", "assets", ["current_custodian_wallet"])
    op.create_index("ix_assets_state", "assets", ["state"])

    # ─── custody_events ───────────────────────────────────────────────────────
    op.create_table(
        "custody_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "asset_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("from_wallet", sa.Text(), nullable=True),
        sa.Column("to_wallet", sa.Text(), nullable=True),
        sa.Column("timestamp", TIMESTAMP(timezone=True), nullable=False),
        sa.Column("location", JSONB(), nullable=True),
        sa.Column("data", JSONB(), nullable=False, server_default="{}"),
        sa.Column("prev_event_hash", sa.Text(), nullable=True),
        sa.Column("event_hash", sa.Text(), nullable=False),
        sa.Column("solana_tx_sig", sa.Text(), nullable=True),
        sa.Column(
            "anchored", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "anchor_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("anchor_last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint(
        "uq_custody_events_hash", "custody_events", ["event_hash"]
    )
    op.create_index(
        "ix_custody_events_asset_timestamp",
        "custody_events",
        ["asset_id", sa.text("timestamp DESC")],
    )
    op.create_index("ix_custody_events_anchored", "custody_events", ["anchored"])


def downgrade() -> None:
    op.drop_table("custody_events")
    op.drop_table("assets")
    op.drop_table("registry_wallets")
