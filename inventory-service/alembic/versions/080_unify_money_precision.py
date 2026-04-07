"""Standardize all monetary columns to Numeric(18,2) to prevent overflow on COP.

Numeric(14,2) caps at ~99M which overflows on real Colombian invoices.
Quantities and unit_prices stay at Numeric(18,4) (precision for fractional units).

Revision ID: 080
Revises: 079
"""
from alembic import op
import sqlalchemy as sa

revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None


# Tables/columns to widen from Numeric(14,2) → Numeric(18,2)
MONEY_COLUMNS = [
    ("sales_orders", "subtotal"),
    ("sales_orders", "tax_amount"),
    ("sales_orders", "discount_amount"),
    ("sales_orders", "total"),
    ("sales_orders", "total_retention"),
    ("sales_orders", "total_with_tax"),
    ("sales_orders", "total_payable"),
    ("sales_orders", "credit_note_amount"),
    ("sales_orders", "debit_note_amount"),
    ("purchase_orders", "subtotal"),
    ("purchase_orders", "tax_amount"),
    ("purchase_orders", "total"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for table, col in MONEY_COLUMNS:
        # Skip if the column doesn't exist (model drift across services).
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": col},
        ).first()
        if not exists:
            continue
        # SAVEPOINT per ALTER so a single failure doesn't poison the
        # surrounding alembic transaction (which then makes every subsequent
        # ALTER fail with InFailedSQLTransactionError on PostgreSQL).
        nested = bind.begin_nested()
        try:
            op.alter_column(
                table,
                col,
                existing_type=sa.Numeric(14, 2),
                type_=sa.Numeric(18, 2),
                existing_nullable=True,
                postgresql_using=f"{col}::numeric(18,2)",
            )
            nested.commit()
        except Exception:
            nested.rollback()


def downgrade() -> None:
    bind = op.get_bind()
    for table, col in MONEY_COLUMNS:
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": col},
        ).first()
        if not exists:
            continue
        nested = bind.begin_nested()
        try:
            op.alter_column(
                table,
                col,
                existing_type=sa.Numeric(18, 2),
                type_=sa.Numeric(14, 2),
                existing_nullable=True,
                postgresql_using=f"{col}::numeric(14,2)",
            )
            nested.commit()
        except Exception:
            nested.rollback()
