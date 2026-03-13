"""Add supplier_type_id to custom_supplier_fields, create custom_warehouse_fields and custom_movement_fields.

Revision ID: 009
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add supplier_type_id to custom_supplier_fields
    op.add_column(
        "custom_supplier_fields",
        sa.Column(
            "supplier_type_id",
            sa.String(36),
            sa.ForeignKey("supplier_types.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    # Drop old unique constraint and create new one with supplier_type_id
    op.drop_constraint("uq_custom_supplier_field_tenant_key", "custom_supplier_fields", type_="unique")
    op.create_unique_constraint(
        "uq_custom_supplier_field_tenant_key_st",
        "custom_supplier_fields",
        ["tenant_id", "field_key", "supplier_type_id"],
    )
    op.create_index(
        "ix_custom_supplier_fields_supplier_type",
        "custom_supplier_fields",
        ["tenant_id", "supplier_type_id"],
    )

    # 2. Create custom_warehouse_fields
    op.create_table(
        "custom_warehouse_fields",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "warehouse_type_id",
            sa.String(36),
            sa.ForeignKey("warehouse_types.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=False),
        sa.Column("field_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "field_key", "warehouse_type_id", name="uq_custom_warehouse_field_tenant_key_wt"),
    )
    op.create_index("ix_custom_warehouse_fields_tenant_id", "custom_warehouse_fields", ["tenant_id"])
    op.create_index("ix_custom_warehouse_fields_warehouse_type", "custom_warehouse_fields", ["tenant_id", "warehouse_type_id"])

    # 3. Create custom_movement_fields
    op.create_table(
        "custom_movement_fields",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "movement_type_id",
            sa.String(36),
            sa.ForeignKey("movement_types.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=False),
        sa.Column("field_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "field_key", "movement_type_id", name="uq_custom_movement_field_tenant_key_mt"),
    )
    op.create_index("ix_custom_movement_fields_tenant_id", "custom_movement_fields", ["tenant_id"])
    op.create_index("ix_custom_movement_fields_movement_type", "custom_movement_fields", ["tenant_id", "movement_type_id"])


def downgrade() -> None:
    op.drop_table("custom_movement_fields")
    op.drop_table("custom_warehouse_fields")
    op.drop_index("ix_custom_supplier_fields_supplier_type", "custom_supplier_fields")
    op.drop_constraint("uq_custom_supplier_field_tenant_key_st", "custom_supplier_fields", type_="unique")
    op.create_unique_constraint(
        "uq_custom_supplier_field_tenant_key",
        "custom_supplier_fields",
        ["tenant_id", "field_key"],
    )
    op.drop_column("custom_supplier_fields", "supplier_type_id")
