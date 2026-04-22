"""Drop is_test_mode from email_provider_configs.

CLAUDE.md regla #0.bis: eliminar toda la logica simulada. Resend no tiene
sandbox y el flag nunca era chequeado en el codigo de envio. Se va.

Revision ID: 020
Revises: 019
"""
from alembic import op


revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("email_provider_configs", "is_test_mode")


def downgrade() -> None:
    import sqlalchemy as sa
    op.add_column(
        "email_provider_configs",
        sa.Column("is_test_mode", sa.Boolean, nullable=False, server_default="false"),
    )
