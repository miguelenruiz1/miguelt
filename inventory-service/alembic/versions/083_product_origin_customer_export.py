"""Product/supplier origin link, customer tax_id_type.

EUDR + export readiness:
- Product/Supplier: link to compliance_plots (cross-DB, validated app-side).
- Customer: tax_id_type (NIT, EORI, VAT, NIF, RUC, CNPJ).

Note: SalesOrder.incoterm and SalesOrder.destination_country already exist
(added in migration 065). We reuse those instead of adding duplicates.

Revision: 083
Revises: 082
"""
from alembic import op
import sqlalchemy as sa


revision = "083"
down_revision = "082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Products (table is `entities`)
    op.add_column("entities", sa.Column("origin_plot_id", sa.String(36), nullable=True))
    op.add_column("entities", sa.Column("origin_plot_code", sa.String(64), nullable=True))

    # Suppliers
    op.add_column("suppliers", sa.Column("origin_plot_id", sa.String(36), nullable=True))
    op.add_column("suppliers", sa.Column("origin_plot_code", sa.String(64), nullable=True))

    # Customers
    op.add_column("customers", sa.Column("tax_id_type", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "tax_id_type")
    op.drop_column("suppliers", "origin_plot_code")
    op.drop_column("suppliers", "origin_plot_id")
    op.drop_column("entities", "origin_plot_code")
    op.drop_column("entities", "origin_plot_id")
