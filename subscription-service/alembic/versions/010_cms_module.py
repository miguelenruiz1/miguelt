"""CMS module — pages, sections, scripts for landing page builder.

Revision ID: 010
Revises: 009
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cms_pages ─────────────────────────────────────────────────────────────
    op.create_table(
        "cms_pages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unpublished_at", sa.DateTime(timezone=True), nullable=True),
        # SEO
        sa.Column("seo_title", sa.String(255), nullable=True),
        sa.Column("seo_description", sa.Text, nullable=True),
        sa.Column("seo_keywords", sa.String(500), nullable=True),
        sa.Column("og_title", sa.String(255), nullable=True),
        sa.Column("og_description", sa.Text, nullable=True),
        sa.Column("og_image", sa.String(500), nullable=True),
        sa.Column("og_type", sa.String(50), nullable=True),
        sa.Column("twitter_card", sa.String(50), nullable=True),
        sa.Column("canonical_url", sa.String(500), nullable=True),
        sa.Column("robots", sa.String(100), nullable=True),
        sa.Column("json_ld", JSONB, nullable=True),
        sa.Column("lang", sa.String(10), nullable=False, server_default="es"),
        # Layout
        sa.Column("navbar_config", JSONB, nullable=True),
        sa.Column("footer_config", JSONB, nullable=True),
        sa.Column("theme_overrides", JSONB, nullable=True),
        # Audit
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cms_pages_status", "cms_pages", ["status"])
    op.create_index("ix_cms_pages_slug", "cms_pages", ["slug"])

    # ── cms_sections ──────────────────────────────────────────────────────────
    op.create_table(
        "cms_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("page_id", sa.String(36), sa.ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("block_type", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_visible", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("css_class", sa.String(255), nullable=True),
        sa.Column("anchor_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cms_sections_page_id", "cms_sections", ["page_id"])
    op.create_index("ix_cms_sections_sort_order", "cms_sections", ["page_id", "sort_order"])

    # ── cms_scripts ───────────────────────────────────────────────────────────
    op.create_table(
        "cms_scripts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("page_id", sa.String(36), sa.ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("placement", sa.String(20), nullable=False, server_default="head"),
        sa.Column("script_content", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cms_scripts_page_id", "cms_scripts", ["page_id"])
    op.create_index("ix_cms_scripts_placement", "cms_scripts", ["placement"])


def downgrade() -> None:
    op.drop_table("cms_scripts")
    op.drop_table("cms_sections")
    op.drop_table("cms_pages")
