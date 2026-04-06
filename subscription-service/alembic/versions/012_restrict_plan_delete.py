"""Change subscriptions.plan_id to ondelete=RESTRICT.

Prevents catastrophic loss of billing history when a plan is hard-deleted.

Revision ID: 012
Revises: 011
"""
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_plan_id_fkey")
    op.create_foreign_key(
        "subscriptions_plan_id_fkey",
        "subscriptions",
        "plans",
        ["plan_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("subscriptions_plan_id_fkey", "subscriptions", type_="foreignkey")
    op.create_foreign_key(
        "subscriptions_plan_id_fkey",
        "subscriptions",
        "plans",
        ["plan_id"],
        ["id"],
        ondelete="CASCADE",
    )
