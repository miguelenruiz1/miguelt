"""Add FK to tenants for anchor_requests/anchor_rules and tighten workflow_states.

- anchor_requests.tenant_id -> FK tenants.id ON DELETE RESTRICT
- anchor_rules.tenant_id    -> FK tenants.id ON DELETE RESTRICT
- workflow_states.tenant_id -> change CASCADE → RESTRICT to match the rest

Revision ID: 019_tenant_fks
Revises: 018_blockchain_err
"""
from alembic import op

revision = "019_tenant_fks"
down_revision = "018_blockchain_err"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # anchor_requests
    op.create_foreign_key(
        "fk_anchor_requests_tenant",
        "anchor_requests",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # anchor_rules
    op.create_foreign_key(
        "fk_anchor_rules_tenant",
        "anchor_rules",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # workflow_states: replace CASCADE with RESTRICT
    op.execute("ALTER TABLE workflow_states DROP CONSTRAINT IF EXISTS workflow_states_tenant_id_fkey")
    op.create_foreign_key(
        "workflow_states_tenant_id_fkey",
        "workflow_states",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_anchor_requests_tenant", "anchor_requests", type_="foreignkey")
    op.drop_constraint("fk_anchor_rules_tenant", "anchor_rules", type_="foreignkey")
    op.drop_constraint("workflow_states_tenant_id_fkey", "workflow_states", type_="foreignkey")
    op.create_foreign_key(
        "workflow_states_tenant_id_fkey",
        "workflow_states",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
