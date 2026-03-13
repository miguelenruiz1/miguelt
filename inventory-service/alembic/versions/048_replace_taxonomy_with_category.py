"""Replace taxonomy system with category — drop vocabulary/term tables,
add default_category_id to product_types, remove vocabulary_id from custom_product_fields.

Revision ID: 048
"""
from alembic import op
import sqlalchemy as sa

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add default_category_id FK to product_types
    op.add_column(
        "product_types",
        sa.Column(
            "default_category_id",
            sa.String(36),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # 2. Drop vocabulary_id FK from custom_product_fields
    op.drop_constraint(
        "fk_custom_field_vocabulary", "custom_product_fields", type_="foreignkey"
    )
    op.drop_column("custom_product_fields", "vocabulary_id")

    # 3. Drop taxonomy tables in dependency order
    op.drop_table("product_term_assignments")
    op.drop_table("taxonomy_terms")
    op.drop_table("taxonomy_vocabularies")


def downgrade() -> None:
    # Recreate taxonomy_vocabularies
    op.create_table(
        "taxonomy_vocabularies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "product_type_id",
            sa.String(36),
            sa.ForeignKey("product_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("allow_multiple", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_vocab_tenant_slug"),
        sa.Index("ix_taxonomy_vocabularies_tenant_id", "tenant_id"),
        sa.Index("ix_taxonomy_vocabularies_pt", "product_type_id"),
    )

    # Recreate taxonomy_terms
    op.create_table(
        "taxonomy_terms",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "vocabulary_id",
            sa.String(36),
            sa.ForeignKey("taxonomy_vocabularies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.String(36),
            sa.ForeignKey("taxonomy_terms.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "vocabulary_id", "slug", name="uq_term_tenant_vocab_slug"),
        sa.Index("ix_taxonomy_terms_tenant_id", "tenant_id"),
        sa.Index("ix_taxonomy_terms_vocab", "vocabulary_id"),
    )

    # Recreate product_term_assignments
    op.create_table(
        "product_term_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "product_id",
            sa.String(36),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "term_id",
            sa.String(36),
            sa.ForeignKey("taxonomy_terms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("product_id", "term_id", name="uq_product_term"),
        sa.Index("ix_product_term_assignments_tenant_id", "tenant_id"),
        sa.Index("ix_product_term_assignments_product", "product_id"),
        sa.Index("ix_product_term_assignments_term", "term_id"),
    )

    # Re-add vocabulary_id to custom_product_fields
    op.add_column(
        "custom_product_fields",
        sa.Column(
            "vocabulary_id",
            sa.String(36),
            sa.ForeignKey("taxonomy_vocabularies.id", ondelete="SET NULL", name="fk_custom_field_vocabulary"),
            nullable=True,
        ),
    )

    # Drop default_category_id from product_types
    op.drop_column("product_types", "default_category_id")
