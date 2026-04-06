"""CHECK constraint on assets.blockchain_status to lock canonical values.

Revision ID: 020_blockchain_check
Revises: 019_tenant_fks
"""
from alembic import op

revision = "020_blockchain_check"
down_revision = "019_tenant_fks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_assets_blockchain_status",
        "assets",
        "blockchain_status IN ('PENDING','CONFIRMED','FAILED','SIMULATED','SKIPPED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_assets_blockchain_status", "assets", type_="check")
