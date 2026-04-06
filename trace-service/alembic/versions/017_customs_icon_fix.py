"""Fix customs custodian icon to one that exists in the icon picker (shield).

Also normalizes any pre-existing 'customs' icon literals to 'shield-check' so
the frontend renderCustodianIcon resolves correctly.

Revision ID: 017_customs_icon
Revises: 016_tenant_indexes
"""
from alembic import op

revision = "017_customs_icon"
down_revision = "016_tenant_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE custodian_types SET icon = 'shield-check' "
        "WHERE slug = 'customs' AND (icon IS NULL OR icon IN ('customs', 'shield', ''))"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE custodian_types SET icon = 'shield' "
        "WHERE slug = 'customs' AND icon = 'shield-check'"
    )
