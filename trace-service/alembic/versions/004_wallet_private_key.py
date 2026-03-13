"""Add encrypted_private_key column to registry_wallets.

Revision ID: 004_wallet_private_key
Revises: 003_multi_tenant
Create Date: 2026-03-02
"""
import sqlalchemy as sa
from alembic import op

revision = "004_wallet_private_key"
down_revision = "003_multi_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "registry_wallets",
        sa.Column("encrypted_private_key", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("registry_wallets", "encrypted_private_key")
