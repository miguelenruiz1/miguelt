"""Make vocabulary.product_type_id nullable, add custom_field.vocabulary_id, add 'reference' field type.

Revision ID: 008
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Make taxonomy_vocabularies.product_type_id nullable
    op.alter_column(
        "taxonomy_vocabularies",
        "product_type_id",
        existing_type=sa.String(36),
        nullable=True,
    )

    # 2. Drop the unique constraint that includes product_type_id (it won't work well with NULLs)
    op.drop_constraint("uq_vocab_tenant_pt_slug", "taxonomy_vocabularies", type_="unique")
    # Replace with a unique on (tenant_id, slug) — slug should be unique per tenant
    op.create_unique_constraint(
        "uq_vocab_tenant_slug",
        "taxonomy_vocabularies",
        ["tenant_id", "slug"],
    )

    # 3. Add vocabulary_id FK to custom_product_fields
    op.add_column(
        "custom_product_fields",
        sa.Column("vocabulary_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_custom_field_vocabulary",
        "custom_product_fields",
        "taxonomy_vocabularies",
        ["vocabulary_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_custom_field_vocabulary", "custom_product_fields", type_="foreignkey")
    op.drop_column("custom_product_fields", "vocabulary_id")

    op.drop_constraint("uq_vocab_tenant_slug", "taxonomy_vocabularies", type_="unique")
    op.create_unique_constraint(
        "uq_vocab_tenant_pt_slug",
        "taxonomy_vocabularies",
        ["tenant_id", "product_type_id", "slug"],
    )

    op.alter_column(
        "taxonomy_vocabularies",
        "product_type_id",
        existing_type=sa.String(36),
        nullable=False,
    )
