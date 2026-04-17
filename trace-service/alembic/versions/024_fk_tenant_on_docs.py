"""Add FK constraint on tenant_id for shipment_documents and trade_documents.

Both tables used `tenant_id: Mapped[uuid.UUID]` as a bare column, with no
referential integrity against `tenants(id)`. Practically that meant deleting
a tenant left orphan rows pointing at a non-existent `tenants.id`. The other
tenant-scoped tables (assets, custody_events, registry_wallets, …) were
already using `ForeignKey("tenants.id", ondelete="RESTRICT")` so this brings
these two laggards in line.

Orphan rows are cleaned up first — attempting to add the FK while any row's
tenant_id doesn't map to an existing tenant would fail. We use ON DELETE
CASCADE here because document rows have no intrinsic value once their
parent tenant is gone (unlike assets / events which we keep for audit).

Revision: 024_fk_tenant_on_docs
Revises: 023_asset_plot_event_qty
"""
from alembic import op


revision = "024_fk_tenant_on_docs"
down_revision = "023_asset_plot_event_qty"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sweep orphan rows before creating the constraint.
    op.execute(
        "DELETE FROM shipment_documents "
        "WHERE tenant_id NOT IN (SELECT id FROM tenants)"
    )
    op.execute(
        "DELETE FROM trade_documents "
        "WHERE tenant_id NOT IN (SELECT id FROM tenants)"
    )

    op.create_foreign_key(
        "fk_shipment_documents_tenant_id",
        source_table="shipment_documents",
        referent_table="tenants",
        local_cols=["tenant_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_trade_documents_tenant_id",
        source_table="trade_documents",
        referent_table="tenants",
        local_cols=["tenant_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_trade_documents_tenant_id", "trade_documents", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_shipment_documents_tenant_id", "shipment_documents", type_="foreignkey"
    )
