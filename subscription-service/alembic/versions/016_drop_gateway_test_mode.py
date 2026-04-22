"""Drop is_test_mode from payment_gateway_configs.

CLAUDE.md regla #0.bis: nada de sandbox para pasarelas en prod. El checkout
de Wompi siempre apunta a checkout.wompi.co (productivo). Si alguien quiere
probar con sandbox de Wompi, que use credenciales de sandbox — Wompi
diferencia por API key, no por URL nuestra.

Revision ID: 016
Revises: 015
"""
from alembic import op


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("payment_gateway_configs", "is_test_mode")


def downgrade() -> None:
    import sqlalchemy as sa
    op.add_column(
        "payment_gateway_configs",
        sa.Column("is_test_mode", sa.Boolean, nullable=False, server_default="false"),
    )
