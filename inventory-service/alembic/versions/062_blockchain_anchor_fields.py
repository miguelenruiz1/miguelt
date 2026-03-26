"""Add blockchain anchor fields to POs, SOs, batches, and movements.

Revision ID: 062
Revises: 061_product_weight_volume
"""
from alembic import op
import sqlalchemy as sa

revision = "062_blockchain_anchor_fields"
down_revision = "061_product_weight_volume"
branch_labels = None
depends_on = None

_TABLES = ["purchase_orders", "sales_orders", "entity_batches", "stock_movements"]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("anchor_hash", sa.String(64), nullable=True))
        op.add_column(table, sa.Column("anchor_status", sa.String(20), nullable=False, server_default="none"))
        op.add_column(table, sa.Column("anchor_tx_sig", sa.String(128), nullable=True))
        op.add_column(table, sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index(f"ix_{table}_anchor_status", table, ["anchor_status"])


def downgrade() -> None:
    for table in _TABLES:
        op.drop_index(f"ix_{table}_anchor_status", table_name=table)
        op.drop_column(table, "anchored_at")
        op.drop_column(table, "anchor_tx_sig")
        op.drop_column(table, "anchor_status")
        op.drop_column(table, "anchor_hash")
