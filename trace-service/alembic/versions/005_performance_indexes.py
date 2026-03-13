"""Add performance indexes.

Revision ID: 005_performance_indexes
Revises: 004_wallet_private_key
Create Date: 2026-03-06
"""
from alembic import op
import sqlalchemy as sa

revision = "005_performance_indexes"
down_revision = "004_wallet_private_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dedicated FK index for custody_events.asset_id (single-column).
    # 001 created a composite (asset_id, timestamp DESC) but this covers
    # pure FK lookups / joins without the sort overhead.
    op.create_index("ix_custody_events_asset_id", "custody_events", ["asset_id"])

    # Composite index for dashboard queries (list assets by tenant + state).
    # 003 created ix_assets_tenant (tenant_id only); this covers the common
    # filtered-by-state query used by the tracking board.
    op.create_index("ix_assets_tenant_state", "assets", ["tenant_id", "state"])

    # NOTE: ix_registry_wallets_pubkey skipped — uq_registry_wallets_pubkey
    #       (unique constraint from 001) already provides an implicit B-tree index.

    # NOTE: ix_registry_wallets_org skipped — already created in 002_organizations.

    # NOTE: ix_custody_events_tenant skipped — custody_events table has no
    #       tenant_id column (events inherit tenant scope via their asset).


def downgrade() -> None:
    op.drop_index("ix_assets_tenant_state", table_name="assets")
    op.drop_index("ix_custody_events_asset_id", table_name="custody_events")
