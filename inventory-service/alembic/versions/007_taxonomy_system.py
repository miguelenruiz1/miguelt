"""Replace EntityType/Bundle/FieldAPI/ProductCategory with taxonomy vocabularies and terms.

Revision ID: 007
Revises: 006
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"


def upgrade() -> None:
    # ─── 1. Drop the "products" view (SELECT * FROM entities) so columns
    # can be dropped safely, then recreate it afterward.
    op.execute("DROP VIEW IF EXISTS products")

    # Drop FK columns from entities.
    # category_id FK was created on original "products" table (001), constraint
    # name kept after table renamed to "entities" (004).
    op.drop_constraint("products_category_id_fkey", "entities", type_="foreignkey")
    op.drop_column("entities", "category_id")

    op.drop_constraint("entities_entity_type_id_fkey", "entities", type_="foreignkey")
    op.drop_column("entities", "entity_type_id")

    op.drop_constraint("entities_bundle_id_fkey", "entities", type_="foreignkey")
    op.drop_column("entities", "bundle_id")

    # Recreate products view without dropped columns
    op.execute("CREATE OR REPLACE VIEW products AS SELECT * FROM entities")

    # ─── 2. Add tracks_serials / tracks_batches to product_types ─────────
    op.add_column(
        "product_types",
        sa.Column("tracks_serials", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "product_types",
        sa.Column("tracks_batches", sa.Boolean, nullable=False, server_default="false"),
    )

    # ─── 3. Drop old tables (reverse dependency order) ───────────────────
    op.drop_table("field_instances")
    op.drop_table("field_storages")
    op.drop_table("entity_bundles")
    op.drop_table("entity_types")
    op.drop_table("product_categories")

    # ─── 4. Create taxonomy tables ───────────────────────────────────────
    op.create_table(
        "taxonomy_vocabularies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "product_type_id",
            sa.String(36),
            sa.ForeignKey("product_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("allow_multiple", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint(
            "tenant_id", "product_type_id", "slug",
            name="uq_vocab_tenant_pt_slug",
        ),
        sa.Index("ix_taxonomy_vocabularies_tenant_id", "tenant_id"),
        sa.Index("ix_taxonomy_vocabularies_pt", "product_type_id"),
    )

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
        sa.UniqueConstraint(
            "tenant_id", "vocabulary_id", "slug",
            name="uq_term_tenant_vocab_slug",
        ),
        sa.Index("ix_taxonomy_terms_tenant_id", "tenant_id"),
        sa.Index("ix_taxonomy_terms_vocab", "vocabulary_id"),
    )

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


def downgrade() -> None:
    op.drop_table("product_term_assignments")
    op.drop_table("taxonomy_terms")
    op.drop_table("taxonomy_vocabularies")

    op.drop_column("product_types", "tracks_batches")
    op.drop_column("product_types", "tracks_serials")

    # Re-create dropped tables and columns would go here
    # (omitted for brevity — destructive migration)
