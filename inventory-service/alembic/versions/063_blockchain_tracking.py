"""Add track_on_chain to products and blockchain_asset_id to batches.

Revision ID: 063
Revises: 062_blockchain_anchor_fields
"""
from alembic import op
import sqlalchemy as sa

revision = "063_blockchain_tracking"
down_revision = "062_blockchain_anchor_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Product: opt-in for on-chain tracking
    op.add_column("entities", sa.Column("track_on_chain", sa.Boolean, nullable=False, server_default="false"))

    # Batch: cNFT asset reference (cross-service to trace-service)
    op.add_column("entity_batches", sa.Column("blockchain_asset_id", sa.String(128), nullable=True))
    op.add_column("entity_batches", sa.Column("blockchain_tx_sig", sa.String(128), nullable=True))
    op.add_column("entity_batches", sa.Column("blockchain_status", sa.String(20), nullable=False, server_default="none"))


def downgrade() -> None:
    op.drop_column("entity_batches", "blockchain_status")
    op.drop_column("entity_batches", "blockchain_tx_sig")
    op.drop_column("entity_batches", "blockchain_asset_id")
    op.drop_column("entities", "track_on_chain")
