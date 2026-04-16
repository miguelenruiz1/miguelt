"""DDS polling fields: validated_at, rejection_reason, last_polled_at.

TRACES NT submission returns a reference_number synchronously, but the DDS
goes through async validation on the EU side (can take minutes to hours).
We poll `retrieveDdsInfoByReferences` periodically to pick up state changes
and persist the verdict on the record. These three columns back that loop.

Also relaxes the `ck_records_declaration_status` CHECK to admit the new
terminal statuses emitted by the polling loop (`validated`, `amended`) as
well as the pre-existing ones.

Revision: 032
Revises: 031_commodity_quality_rspo
"""
revision = "032_dds_polling_fields"
down_revision = "031_commodity_quality_rspo"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


_ALLOWED_STATUSES = (
    "'not_required','pending','submitted','accepted','rejected',"
    "'validated','amended'"
)


def upgrade() -> None:
    op.add_column(
        "compliance_records",
        sa.Column("declaration_validated_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "compliance_records",
        sa.Column("declaration_rejection_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "compliance_records",
        sa.Column("declaration_last_polled_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Expand the CHECK to include the new statuses emitted by the polling loop.
    op.drop_constraint(
        "ck_records_declaration_status",
        "compliance_records",
        type_="check",
    )
    op.create_check_constraint(
        "ck_records_declaration_status",
        "compliance_records",
        f"declaration_status IN ({_ALLOWED_STATUSES})",
    )

    # Helper index for the polling loop selection.
    op.create_index(
        "ix_records_decl_status_polled",
        "compliance_records",
        ["declaration_status", "declaration_last_polled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_records_decl_status_polled", table_name="compliance_records")
    op.drop_constraint(
        "ck_records_declaration_status",
        "compliance_records",
        type_="check",
    )
    op.create_check_constraint(
        "ck_records_declaration_status",
        "compliance_records",
        "declaration_status IN ('not_required','pending','submitted','accepted','rejected')",
    )
    op.drop_column("compliance_records", "declaration_last_polled_at")
    op.drop_column("compliance_records", "declaration_rejection_reason")
    op.drop_column("compliance_records", "declaration_validated_at")
