"""Convert business_partners.credit_limit / discount_percent to Numeric.

Integer was wrong for monetary amounts (COP loses decimals) and percentages
(no support for 12.5% etc.). Adds CHECK constraint for discount_percent range.

Revision ID: 078
Revises: 077
"""
from alembic import op
import sqlalchemy as sa

revision = "078"
down_revision = "077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "business_partners",
        "credit_limit",
        existing_type=sa.Integer(),
        type_=sa.Numeric(18, 2),
        existing_nullable=False,
        existing_server_default="0",
        postgresql_using="credit_limit::numeric(18,2)",
    )
    op.alter_column(
        "business_partners",
        "discount_percent",
        existing_type=sa.Integer(),
        type_=sa.Numeric(5, 2),
        existing_nullable=False,
        existing_server_default="0",
        postgresql_using="discount_percent::numeric(5,2)",
    )
    op.create_check_constraint(
        "ck_business_partners_discount_range",
        "business_partners",
        "discount_percent >= 0 AND discount_percent <= 100",
    )
    op.create_check_constraint(
        "ck_business_partners_credit_nonneg",
        "business_partners",
        "credit_limit >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_business_partners_discount_range", "business_partners", type_="check")
    op.drop_constraint("ck_business_partners_credit_nonneg", "business_partners", type_="check")
    op.alter_column(
        "business_partners",
        "credit_limit",
        existing_type=sa.Numeric(18, 2),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="credit_limit::integer",
    )
    op.alter_column(
        "business_partners",
        "discount_percent",
        existing_type=sa.Numeric(5, 2),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="discount_percent::integer",
    )
