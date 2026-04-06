"""Make user email/username unique per tenant instead of globally.

Closes a multi-tenancy blocker: two different tenants could not have the
same admin email like 'admin@empresa.com' until this change.

Revision ID: 016
Revises: 015
"""
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop legacy global unique constraints (if they exist under the auto names)
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_key")
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    op.execute("DROP INDEX IF EXISTS ix_users_username")

    op.create_unique_constraint(
        "uq_users_tenant_email", "users", ["tenant_id", "email"]
    )
    op.create_unique_constraint(
        "uq_users_tenant_username", "users", ["tenant_id", "username"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_tenant_email", "users", type_="unique")
    op.drop_constraint("uq_users_tenant_username", "users", type_="unique")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email)")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_username_key UNIQUE (username)")
