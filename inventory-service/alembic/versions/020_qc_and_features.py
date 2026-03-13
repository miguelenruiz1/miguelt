"""Add QC blocking, dispatch rules, and entry rules to product_types and stock_levels.

Revision ID: 020
Revises: 019
Create Date: 2026-03-07
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── stock_levels: add qc_status ──────────────────────────────────────
    op.add_column("stock_levels", sa.Column(
        "qc_status", sa.String(20), nullable=False, server_default="approved",
    ))

    # ── product_types: add requires_qc, entry_rule_location_id, dispatch_rule ─
    op.add_column("product_types", sa.Column(
        "requires_qc", sa.Boolean(), nullable=False, server_default="false",
    ))
    op.add_column("product_types", sa.Column(
        "entry_rule_location_id", sa.String(36),
        sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.add_column("product_types", sa.Column(
        "dispatch_rule", sa.String(10), nullable=False, server_default="fifo",
    ))


def downgrade() -> None:
    op.drop_column("product_types", "dispatch_rule")
    op.drop_column("product_types", "entry_rule_location_id")
    op.drop_column("product_types", "requires_qc")
    op.drop_column("stock_levels", "qc_status")
