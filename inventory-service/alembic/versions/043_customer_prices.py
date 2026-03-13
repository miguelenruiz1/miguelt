"""Customer special pricing: customer_prices, customer_price_history tables
and price_source / customer_price_id columns on sales_order_lines."""
from alembic import op
import sqlalchemy as sa

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── customer_prices ────────────────────────────────────────────────
    op.create_table(
        "customer_prices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.String(36), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("price", sa.Numeric(12, 4), nullable=False),
        sa.Column("min_quantity", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="COP"),
        sa.Column("valid_from", sa.Date, nullable=False),
        sa.Column("valid_to", sa.Date, nullable=True),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_customer_price_lookup", "customer_prices", ["tenant_id", "customer_id", "product_id", "is_active"])
    op.create_index("ix_customer_price_validity", "customer_prices", ["valid_from", "valid_to"])

    # ── customer_price_history ─────────────────────────────────────────
    op.create_table(
        "customer_price_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("customer_price_id", sa.String(36), sa.ForeignKey("customer_prices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("old_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("new_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("changed_by", sa.String(100), nullable=False),
        sa.Column("changed_by_name", sa.String(200), nullable=True),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_price_history_customer_product", "customer_price_history", ["customer_id", "product_id"])

    # ── new columns on sales_order_lines ───────────────────────────────
    op.add_column("sales_order_lines", sa.Column("price_source", sa.String(20), nullable=True))
    op.add_column("sales_order_lines", sa.Column(
        "customer_price_id", sa.String(36),
        sa.ForeignKey("customer_prices.id", ondelete="SET NULL"),
        nullable=True,
    ))


def downgrade() -> None:
    op.drop_column("sales_order_lines", "customer_price_id")
    op.drop_column("sales_order_lines", "price_source")
    op.drop_index("ix_price_history_customer_product", table_name="customer_price_history")
    op.drop_table("customer_price_history")
    op.drop_index("ix_customer_price_validity", table_name="customer_prices")
    op.drop_index("ix_customer_price_lookup", table_name="customer_prices")
    op.drop_table("customer_prices")
