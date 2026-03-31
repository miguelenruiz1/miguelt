"""Add missing FK constraint on compliance_risk_assessments.record_id.

Revision ID: 010_risk_fk
Revises: 009_supply_chain_nodes
"""
from alembic import op

revision = "010_risk_fk"
down_revision = "009_supply_chain_nodes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_risk_assessments_record_id",
        "compliance_risk_assessments",
        "compliance_records",
        ["record_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_risk_assessments_record_id", "compliance_risk_assessments", type_="foreignkey")
