"""Add evidence columns (photo/signature) to custody_events for Proof of Delivery.

Revision ID: 012_evidence
Revises: 011_freight_costs
"""
from alembic import op
import sqlalchemy as sa

revision = "012_evidence"
down_revision = "011_freight_costs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("custody_events", sa.Column("evidence_url", sa.Text, nullable=True))
    op.add_column("custody_events", sa.Column("evidence_hash", sa.Text, nullable=True))
    op.add_column("custody_events", sa.Column("evidence_type", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("custody_events", "evidence_type")
    op.drop_column("custody_events", "evidence_hash")
    op.drop_column("custody_events", "evidence_url")
