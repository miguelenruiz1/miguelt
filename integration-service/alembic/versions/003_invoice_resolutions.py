"""Add invoice_resolutions table.

Revision: 003
Down revision: 002
"""

revision = "003"
down_revision = "002"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "invoice_resolutions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("resolution_number", sa.String(50), nullable=False),
        sa.Column("prefix", sa.String(10), nullable=False),
        sa.Column("range_from", sa.Integer, nullable=False),
        sa.Column("range_to", sa.Integer, nullable=False),
        sa.Column("current_number", sa.Integer, nullable=False, server_default="0"),
        sa.Column("valid_from", sa.Date, nullable=False),
        sa.Column("valid_to", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_invoice_resolutions_tenant_id", "invoice_resolutions", ["tenant_id"])

    # Partial unique index: only one active resolution per tenant+provider
    op.execute("""
        CREATE UNIQUE INDEX ix_resolution_tenant_provider_active
        ON invoice_resolutions (tenant_id, provider)
        WHERE is_active = true
    """)

    # Seed default sandbox resolution for existing tenants
    op.execute("""
        INSERT INTO invoice_resolutions (id, tenant_id, provider, is_active,
            resolution_number, prefix, range_from, range_to, current_number,
            valid_from, valid_to)
        SELECT
            gen_random_uuid()::text,
            ic.tenant_id,
            'sandbox',
            true,
            '18760000001',
            'SANDBOX',
            990000000,
            995000000,
            0,
            '2019-01-19',
            '2030-01-19'
        FROM (SELECT DISTINCT tenant_id FROM integration_configs) ic
        WHERE NOT EXISTS (
            SELECT 1 FROM invoice_resolutions ir
            WHERE ir.tenant_id = ic.tenant_id AND ir.provider = 'sandbox'
        )
    """)


def downgrade() -> None:
    op.drop_index("ix_resolution_tenant_provider_active", "invoice_resolutions")
    op.drop_index("ix_invoice_resolutions_tenant_id", "invoice_resolutions")
    op.drop_table("invoice_resolutions")
