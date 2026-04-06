"""Add pg_trgm GIN indexes for fast ILIKE searches on Product/BusinessPartner.

Replaces sequential scans with index lookups for the search bars in
products, partners, customers, suppliers listings.

Revision ID: 079
Revises: 078
"""
from alembic import op

revision = "079"
down_revision = "078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable extension (no-op if already there)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Product name + sku GIN trigram indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entities_name_trgm "
        "ON entities USING gin (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entities_sku_trgm "
        "ON entities USING gin (sku gin_trgm_ops)"
    )

    # BusinessPartner name + code + email
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_business_partners_name_trgm "
        "ON business_partners USING gin (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_business_partners_code_trgm "
        "ON business_partners USING gin (code gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entities_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_entities_sku_trgm")
    op.execute("DROP INDEX IF EXISTS ix_business_partners_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_business_partners_code_trgm")
