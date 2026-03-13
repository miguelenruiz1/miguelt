"""PO consolidation support: new columns and consolidated status."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_orders", sa.Column("is_consolidated", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("purchase_orders", sa.Column("consolidated_from_ids", JSONB, nullable=True))
    op.add_column("purchase_orders", sa.Column("consolidated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("purchase_orders", sa.Column("consolidated_by", sa.String(100), nullable=True))
    op.add_column("purchase_orders", sa.Column("parent_consolidated_id", sa.String(36), sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    op.drop_column("purchase_orders", "parent_consolidated_id")
    op.drop_column("purchase_orders", "consolidated_by")
    op.drop_column("purchase_orders", "consolidated_at")
    op.drop_column("purchase_orders", "consolidated_from_ids")
    op.drop_column("purchase_orders", "is_consolidated")
