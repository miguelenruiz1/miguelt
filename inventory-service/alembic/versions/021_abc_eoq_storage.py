"""ABC classification, EOQ, rotation policy, storage cost."""
from alembic import op
import sqlalchemy as sa

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("warehouses", sa.Column("cost_per_sqm", sa.Numeric(12, 2), nullable=True))
    op.add_column("warehouses", sa.Column("total_area_sqm", sa.Numeric(12, 2), nullable=True))
    op.add_column("product_types", sa.Column("rotation_target_months", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("product_types", "rotation_target_months")
    op.drop_column("warehouses", "total_area_sqm")
    op.drop_column("warehouses", "cost_per_sqm")
