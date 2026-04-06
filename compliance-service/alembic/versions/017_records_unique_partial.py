"""Replace compliance_records UNIQUE(tenant_id,asset_id,framework_id) with two
partial indexes so 'standalone' records (asset_id IS NULL) get one-per-framework
constraint while linked records keep their unique-per-asset rule.

Revision ID: 017_records_partial
Revises: 016_plot_checks
"""
from alembic import op

revision = "017_records_partial"
down_revision = "016_plot_checks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the legacy multi-column UNIQUE so NULL asset_id no longer escapes
    # the constraint via Postgres' "NULLs distinct" semantics.
    op.execute(
        "ALTER TABLE compliance_records "
        "DROP CONSTRAINT IF EXISTS uq_record_asset_framework"
    )
    # Linked records: at most one per (tenant, asset, framework)
    op.create_index(
        "uq_record_asset_framework_linked",
        "compliance_records",
        ["tenant_id", "asset_id", "framework_id"],
        unique=True,
        postgresql_where=op.f("asset_id IS NOT NULL"),
    )
    # Standalone records: at most one per (tenant, framework) when no asset
    op.create_index(
        "uq_record_standalone_framework",
        "compliance_records",
        ["tenant_id", "framework_id"],
        unique=True,
        postgresql_where=op.f("asset_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_record_asset_framework_linked", table_name="compliance_records")
    op.drop_index("uq_record_standalone_framework", table_name="compliance_records")
    op.create_unique_constraint(
        "uq_record_asset_framework",
        "compliance_records",
        ["tenant_id", "asset_id", "framework_id"],
    )
