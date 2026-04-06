"""Make audit_logs append-only via PL/pgSQL trigger and add retention helper.

- BEFORE UPDATE/DELETE trigger raises an exception so audit rows can't be
  silently modified by application bugs or compromised admins.
- Adds an index on (user_id, created_at) to support efficient PII purging
  when a user is deleted or requests Hábeas Data / GDPR removal.

Revision ID: 017
Revises: 016
"""
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_logs_block_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only — UPDATE/DELETE blocked';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER trg_audit_logs_block_update "
        "BEFORE UPDATE ON audit_logs "
        "FOR EACH ROW EXECUTE FUNCTION audit_logs_block_mutation()"
    )
    op.execute(
        "CREATE TRIGGER trg_audit_logs_block_delete "
        "BEFORE DELETE ON audit_logs "
        "FOR EACH ROW EXECUTE FUNCTION audit_logs_block_mutation()"
    )

    # Helpful index for PII anonymization queries (find all rows for a user)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_created "
        "ON audit_logs (user_id, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_block_update ON audit_logs")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_block_delete ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_block_mutation()")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_user_created")
