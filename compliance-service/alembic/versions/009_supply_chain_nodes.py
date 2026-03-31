"""Add compliance_supply_chain_nodes table — EUDR Art. 9.1.e-f.

Revision ID: 009_supply_chain_nodes
Revises: 008_risk_assessments
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "009_supply_chain_nodes"
down_revision = "008_risk_assessments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_supply_chain_nodes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("record_id", UUID(as_uuid=True), sa.ForeignKey("compliance_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_order", sa.Integer, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("actor_name", sa.Text, nullable=False),
        sa.Column("actor_address", sa.Text, nullable=True),
        sa.Column("actor_country", sa.Text, nullable=True),
        sa.Column("actor_tax_id", sa.Text, nullable=True),
        sa.Column("actor_eori", sa.Text, nullable=True),
        sa.Column("handoff_date", sa.Date, nullable=True),
        sa.Column("quantity_kg", sa.Numeric(12, 4), nullable=True),
        sa.Column("verification_status", sa.Text, nullable=False, server_default="unverified"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("record_id", "sequence_order", name="uq_sc_record_sequence"),
        sa.Index("ix_sc_tenant", "tenant_id"),
        sa.Index("ix_sc_record", "record_id"),
    )


def downgrade() -> None:
    op.drop_table("compliance_supply_chain_nodes")
