"""Add missing tenant_id to event_status_logs, event_impacts, variant_attribute_options.
Also add missing unique constraint on categories(tenant_id, slug).
Also add missing indexes on event_impacts and variant_attribute_options.

Revision ID: 067
Revises: 066
"""
from alembic import op
import sqlalchemy as sa

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── event_status_logs: add tenant_id ─────────────────────────────────────
    op.add_column("event_status_logs", sa.Column("tenant_id", sa.String(255), nullable=True))

    # Backfill from parent inventory_events
    op.execute("""
        UPDATE event_status_logs esl
        SET tenant_id = ie.tenant_id
        FROM inventory_events ie
        WHERE esl.event_id = ie.id
          AND esl.tenant_id IS NULL
    """)

    # Set NOT NULL after backfill (allow empty tables)
    op.execute("""
        UPDATE event_status_logs SET tenant_id = 'default' WHERE tenant_id IS NULL
    """)
    op.alter_column("event_status_logs", "tenant_id", nullable=False)
    op.create_index("ix_event_status_logs_tenant_id", "event_status_logs", ["tenant_id"])

    # ── event_impacts: add tenant_id ─────────────────────────────────────────
    op.add_column("event_impacts", sa.Column("tenant_id", sa.String(255), nullable=True))

    op.execute("""
        UPDATE event_impacts ei
        SET tenant_id = ie.tenant_id
        FROM inventory_events ie
        WHERE ei.event_id = ie.id
          AND ei.tenant_id IS NULL
    """)

    op.execute("""
        UPDATE event_impacts SET tenant_id = 'default' WHERE tenant_id IS NULL
    """)
    op.alter_column("event_impacts", "tenant_id", nullable=False)
    op.create_index("ix_event_impacts_tenant_id", "event_impacts", ["tenant_id"])
    op.create_index("ix_event_impacts_event_id", "event_impacts", ["event_id"])

    # ── variant_attribute_options: add tenant_id ─────────────────────────────
    op.add_column("variant_attribute_options", sa.Column("tenant_id", sa.String(255), nullable=True))

    op.execute("""
        UPDATE variant_attribute_options vao
        SET tenant_id = va.tenant_id
        FROM variant_attributes va
        WHERE vao.attribute_id = va.id
          AND vao.tenant_id IS NULL
    """)

    op.execute("""
        UPDATE variant_attribute_options SET tenant_id = 'default' WHERE tenant_id IS NULL
    """)
    op.alter_column("variant_attribute_options", "tenant_id", nullable=False)
    op.create_index("ix_variant_attribute_options_tenant_id", "variant_attribute_options", ["tenant_id"])
    op.create_index("ix_variant_attribute_options_attribute_id", "variant_attribute_options", ["attribute_id"])

    # ── categories: add missing unique constraint ────────────────────────────
    op.create_unique_constraint("uq_category_tenant_slug", "categories", ["tenant_id", "slug"])


def downgrade() -> None:
    op.drop_constraint("uq_category_tenant_slug", "categories", type_="unique")

    op.drop_index("ix_variant_attribute_options_attribute_id", "variant_attribute_options")
    op.drop_index("ix_variant_attribute_options_tenant_id", "variant_attribute_options")
    op.drop_column("variant_attribute_options", "tenant_id")

    op.drop_index("ix_event_impacts_event_id", "event_impacts")
    op.drop_index("ix_event_impacts_tenant_id", "event_impacts")
    op.drop_column("event_impacts", "tenant_id")

    op.drop_index("ix_event_status_logs_tenant_id", "event_status_logs")
    op.drop_column("event_status_logs", "tenant_id")
