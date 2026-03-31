"""Add EUDR compliance gaps: plot establishment_date/renovation, record activity_type,
record signatory fields.

Based on EUDR webinar findings — Colombia readiness analysis.

Revision ID: 006_eudr_gaps
Revises: 005_certificates
"""
from alembic import op
import sqlalchemy as sa

revision = "006_eudr_gaps"
down_revision = "005_certificates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Gap 1: Fecha de establecimiento del cultivo en CompliancePlot
    op.add_column("compliance_plots", sa.Column("establishment_date", sa.Date, nullable=True))
    op.add_column("compliance_plots", sa.Column("crop_type", sa.Text, nullable=True))
    op.add_column("compliance_plots", sa.Column("renovation_date", sa.Date, nullable=True))
    op.add_column("compliance_plots", sa.Column("renovation_type", sa.Text, nullable=True))

    # Gap 2: Tipo de actividad en ComplianceRecord (Anexo II #2)
    op.add_column("compliance_records", sa.Column(
        "activity_type", sa.Text, nullable=False, server_default="export"
    ))

    # Gap 3: Firma digital del operador (Anexo II #10)
    op.add_column("compliance_records", sa.Column("signatory_name", sa.Text, nullable=True))
    op.add_column("compliance_records", sa.Column("signatory_role", sa.Text, nullable=True))
    op.add_column("compliance_records", sa.Column("signatory_date", sa.Date, nullable=True))

    # Gap bonus: Referencias a DDS previos (Anexo II #8)
    op.add_column("compliance_records", sa.Column(
        "prior_dds_references", sa.JSON, nullable=True
    ))


def downgrade() -> None:
    op.drop_column("compliance_records", "prior_dds_references")
    op.drop_column("compliance_records", "signatory_date")
    op.drop_column("compliance_records", "signatory_role")
    op.drop_column("compliance_records", "signatory_name")
    op.drop_column("compliance_records", "activity_type")
    op.drop_column("compliance_plots", "renovation_type")
    op.drop_column("compliance_plots", "renovation_date")
    op.drop_column("compliance_plots", "crop_type")
    op.drop_column("compliance_plots", "establishment_date")
