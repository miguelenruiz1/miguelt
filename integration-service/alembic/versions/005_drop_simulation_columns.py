"""Drop simulation_mode + is_test_mode from integration_configs.

CLAUDE.md regla #0.bis: eliminar toda la logica de simulacion. Las facturas
a MATIAS/DIAN siempre salen al endpoint productivo. Si un tenant quiere
sandbox, usa credenciales de sandbox (API key del proveedor), no un flag
nuestro.

Revision ID: 005
Revises: 004
"""
from alembic import op


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("integration_configs", "simulation_mode")
    op.drop_column("integration_configs", "is_test_mode")


def downgrade() -> None:
    import sqlalchemy as sa
    op.add_column(
        "integration_configs",
        sa.Column("is_test_mode", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "integration_configs",
        sa.Column("simulation_mode", sa.Boolean(), nullable=False, server_default="false"),
    )
