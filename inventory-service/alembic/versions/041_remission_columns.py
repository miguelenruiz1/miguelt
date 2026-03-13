"""Add remission columns to sales_orders."""
from alembic import op
import sqlalchemy as sa

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_orders", sa.Column("remission_number", sa.String(50), nullable=True))
    op.add_column("sales_orders", sa.Column("remission_generated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_orders", "remission_generated_at")
    op.drop_column("sales_orders", "remission_number")
