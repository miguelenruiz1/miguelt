"""Add compliance_risk_assessments table — EUDR Art. 10-11.

Revision ID: 008_risk_assessments
Revises: 007_document_links
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "008_risk_assessments"
down_revision = "007_document_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_risk_assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("record_id", UUID(as_uuid=True), nullable=False),
        sa.Column("assessed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("assessed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Step 1: Country risk
        sa.Column("country_risk_level", sa.Text, nullable=True),
        sa.Column("country_risk_notes", sa.Text, nullable=True),
        sa.Column("country_benchmarking_source", sa.Text, nullable=True),
        # Step 2: Supply chain
        sa.Column("supply_chain_risk_level", sa.Text, nullable=True),
        sa.Column("supply_chain_notes", sa.Text, nullable=True),
        sa.Column("supplier_verification_status", sa.Text, nullable=False, server_default="not_started"),
        sa.Column("traceability_confidence", sa.Text, nullable=False, server_default="none"),
        # Step 3: Regional / product
        sa.Column("regional_risk_level", sa.Text, nullable=True),
        sa.Column("deforestation_prevalence", sa.Text, nullable=True),
        sa.Column("indigenous_rights_risk", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("corruption_index_note", sa.Text, nullable=True),
        # Mitigation
        sa.Column("mitigation_measures", JSONB, nullable=True),
        sa.Column("additional_info_requested", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("independent_audit_required", sa.Boolean, nullable=False, server_default=sa.text("false")),
        # Conclusion
        sa.Column("overall_risk_level", sa.Text, nullable=True),
        sa.Column("conclusion", sa.Text, nullable=True),
        sa.Column("conclusion_notes", sa.Text, nullable=True),
        # Meta
        sa.Column("status", sa.Text, nullable=False, server_default="draft"),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "record_id", name="uq_risk_tenant_record"),
        sa.Index("ix_risk_tenant", "tenant_id"),
        sa.Index("ix_risk_record", "record_id"),
    )


def downgrade() -> None:
    op.drop_table("compliance_risk_assessments")
