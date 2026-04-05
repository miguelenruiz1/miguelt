"""Add DIAN fiscal fields to business_partners for e-invoicing.

Revision ID: 073
Revises: 072
"""
from alembic import op
import sqlalchemy as sa

revision = "073"
down_revision = "072"


def upgrade() -> None:
    op.add_column("business_partners", sa.Column("dv", sa.String(1), nullable=True))
    op.add_column("business_partners", sa.Column("document_type", sa.String(10), nullable=False, server_default="CC"))
    op.add_column("business_partners", sa.Column("organization_type", sa.Integer(), nullable=False, server_default="2"))
    op.add_column("business_partners", sa.Column("tax_regime", sa.Integer(), nullable=False, server_default="2"))
    op.add_column("business_partners", sa.Column("tax_liability", sa.Integer(), nullable=False, server_default="7"))
    op.add_column("business_partners", sa.Column("municipality_id", sa.Integer(), nullable=False, server_default="149"))
    op.add_column("business_partners", sa.Column("company_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("business_partners", "company_name")
    op.drop_column("business_partners", "municipality_id")
    op.drop_column("business_partners", "tax_liability")
    op.drop_column("business_partners", "tax_regime")
    op.drop_column("business_partners", "organization_type")
    op.drop_column("business_partners", "document_type")
    op.drop_column("business_partners", "dv")
