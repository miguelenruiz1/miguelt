"""Feature toggles for tenant inventory config.

Revision ID: 054
Revises: 053
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None

FEATURES = [
    ("feature_lotes", "true"),
    ("feature_seriales", "true"),
    ("feature_variantes", "true"),
    ("feature_conteo", "true"),
    ("feature_escaner", "false"),
    ("feature_picking", "true"),
    ("feature_eventos", "true"),
    ("feature_kardex", "true"),
    ("feature_precios", "true"),
    ("feature_aprobaciones", "false"),
]


def upgrade() -> None:
    for name, default in FEATURES:
        op.add_column("tenant_inventory_configs", sa.Column(name, sa.Boolean, server_default=default, nullable=False))


def downgrade() -> None:
    for name, _ in reversed(FEATURES):
        op.drop_column("tenant_inventory_configs", name)
