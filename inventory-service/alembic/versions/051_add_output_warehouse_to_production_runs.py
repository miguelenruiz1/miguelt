"""Add output_warehouse_id to production_runs.

Allows choosing a different warehouse for the finished product output,
separate from the warehouse where components are consumed.
"""

revision = "051"
down_revision = "050"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "production_runs",
        sa.Column(
            "output_warehouse_id",
            sa.String(36),
            sa.ForeignKey("warehouses.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("production_runs", "output_warehouse_id")
