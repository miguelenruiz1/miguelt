"""Create compliance_records table.

Revision ID: 003_records
Revises: 002_plots
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
import uuid

revision = "003_records"
down_revision = "002_plots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "framework_id",
            UUID(as_uuid=True),
            sa.ForeignKey("compliance_frameworks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("framework_slug", sa.Text(), nullable=False),

        # Product identification (EUDR Art. 9.1.a, 9.1.b)
        sa.Column("hs_code", sa.Text(), nullable=True),
        sa.Column("commodity_type", sa.Text(), nullable=True),
        sa.Column("product_description", sa.Text(), nullable=True),
        sa.Column("scientific_name", sa.Text(), nullable=True),
        sa.Column("quantity_kg", sa.Numeric(12, 4), nullable=True),
        sa.Column("quantity_unit", sa.Text(), nullable=False, server_default="'kg'"),
        sa.Column("country_of_production", sa.Text(), nullable=True),

        # Production period (EUDR Art. 9.1.d)
        sa.Column("production_period_start", sa.Date(), nullable=True),
        sa.Column("production_period_end", sa.Date(), nullable=True),

        # Supply chain (EUDR Art. 9.1.e, 9.1.f)
        sa.Column("supplier_name", sa.Text(), nullable=True),
        sa.Column("supplier_address", sa.Text(), nullable=True),
        sa.Column("supplier_email", sa.Text(), nullable=True),
        sa.Column("buyer_name", sa.Text(), nullable=True),
        sa.Column("buyer_address", sa.Text(), nullable=True),
        sa.Column("buyer_email", sa.Text(), nullable=True),

        # EU export specific
        sa.Column("operator_eori", sa.Text(), nullable=True),

        # Declarations (EUDR Art. 9.1.g, 9.1.h)
        sa.Column("deforestation_free_declaration", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("legal_compliance_declaration", sa.Boolean(), nullable=False, server_default="false"),

        # Document hashes
        sa.Column("legal_cert_hash", sa.Text(), nullable=True),
        sa.Column("deforestation_evidence_hash", sa.Text(), nullable=True),

        # DDS / declaration
        sa.Column("declaration_reference", sa.Text(), nullable=True),
        sa.Column("declaration_submission_date", sa.Date(), nullable=True),
        sa.Column("declaration_status", sa.Text(), nullable=False, server_default="'not_required'"),
        sa.Column("declaration_url", sa.Text(), nullable=True),

        # Status
        sa.Column("compliance_status", sa.Text(), nullable=False, server_default="'incomplete'"),
        sa.Column("last_validated_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("validation_result", JSONB(), nullable=True),
        sa.Column("missing_fields", JSONB(), nullable=True),

        # Retention
        sa.Column("documents_retention_until", sa.Date(), nullable=True),

        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),

        sa.UniqueConstraint("tenant_id", "asset_id", "framework_id", name="uq_record_asset_framework"),
        sa.Index("ix_records_tenant", "tenant_id"),
        sa.Index("ix_records_asset", "asset_id"),
        sa.Index("ix_records_framework", "framework_id"),
        sa.Index("ix_records_status", "compliance_status"),
    )


def downgrade() -> None:
    op.drop_table("compliance_records")
