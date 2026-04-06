"""Add tenant_id to compliance_integrations and switch unique constraint to (tenant_id, provider).

Existing rows are migrated to the default tenant.

Revision ID: 014_integ_tenant
Revises: 013_asset_optional
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "014_integ_tenant"
down_revision = "013_asset_optional"


DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # Add tenant_id nullable, backfill with default tenant, then NOT NULL.
    op.add_column(
        "compliance_integrations",
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
    )
    op.execute(f"UPDATE compliance_integrations SET tenant_id = '{DEFAULT_TENANT}'::uuid WHERE tenant_id IS NULL")
    op.alter_column("compliance_integrations", "tenant_id", nullable=False)

    # Drop the legacy unique INDEX created in migration 011
    # (PostgreSQL: a unique column may be backed by either a constraint or an index).
    op.execute("DROP INDEX IF EXISTS ix_compliance_integrations_provider")
    # Also drop the auto-generated unique constraint name (when SQLAlchemy
    # created it from `unique=True` on the Column rather than an explicit Index).
    op.execute("ALTER TABLE compliance_integrations DROP CONSTRAINT IF EXISTS compliance_integrations_provider_key")

    op.create_unique_constraint(
        "uq_integration_tenant_provider",
        "compliance_integrations",
        ["tenant_id", "provider"],
    )
    op.create_index(
        "ix_compliance_integrations_tenant_id",
        "compliance_integrations",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_compliance_integrations_tenant_id", table_name="compliance_integrations")
    op.drop_constraint("uq_integration_tenant_provider", "compliance_integrations", type_="unique")
    op.create_unique_constraint(
        "compliance_integrations_provider_key",
        "compliance_integrations",
        ["provider"],
    )
    op.drop_column("compliance_integrations", "tenant_id")
