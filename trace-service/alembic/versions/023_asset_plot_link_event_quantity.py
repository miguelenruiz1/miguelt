"""Asset plot link, custody event quantities, location typing.

Adds:
- assets.plot_id (UUID, NULL): cross-DB pointer to compliance_plots.id. No FK
  because compliance lives in a separate Postgres DB; integrity validated at
  app layer.
- custody_event_quantities table: per-event quantity changes (cereza→
  pergamino→verde) with merma calculation. Many quantities per event allowed
  but typical use is one row per beneficio/trilla event.

Note: custody_events.location stays JSONB; shape ({lat,lng,city,country,
accuracy_m}) is enforced at the Pydantic schema layer, not at the DB level —
keeps existing rows readable.

Revision: 023_asset_plot_event_qty
Revises: 022_event_custody_mode
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "023_asset_plot_event_qty"
down_revision = "022_event_custody_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assets",
        sa.Column("plot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_assets_plot_id", "assets", ["plot_id"])

    op.create_table(
        "custody_event_quantities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("custody_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(20), nullable=False),
        sa.Column("previous_quantity", sa.Numeric(18, 4), nullable=True),
        sa.Column("previous_uom", sa.String(20), nullable=True),
        sa.Column("merma_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("quantity > 0", name="ck_ceq_quantity_positive"),
    )
    op.create_index(
        "ix_ceq_event_id", "custody_event_quantities", ["event_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_ceq_event_id", table_name="custody_event_quantities")
    op.drop_table("custody_event_quantities")
    op.drop_index("ix_assets_plot_id", table_name="assets")
    op.drop_column("assets", "plot_id")
