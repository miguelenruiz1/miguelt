"""Multi-commodity support: commodity_type on plots, cadmium + RSPO on records/certs.

Coffee + cacao + palma require different EUDR / market quality fields:
- commodity_type: discriminator for UI filters and validation branches.
- cadmium_*: cacao-specific — EU Regulation 2023/915 caps Cd in cocoa
  derivatives at 0.60 mg/kg for final chocolate. Importers demand lab test
  evidence at batch/shipment level.
- rspo_trace_model: palm-specific — RSPO chain-of-custody model declared
  per record / per certificate (mass balance / segregated / identity
  preserved). Required on DDS additionalInformation block for palma.

Revision: 031
Revises: 030_plot_nuts_datum
"""
revision = "031_commodity_quality_rspo"
down_revision = "030_plot_nuts_datum"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


COMMODITY_VALUES = "('coffee','cacao','palm','other')"
RSPO_VALUES = "('mass_balance','segregated','identity_preserved')"


def upgrade() -> None:
    # compliance_plots.commodity_type
    op.add_column(
        "compliance_plots",
        sa.Column("commodity_type", sa.String(length=20), nullable=True),
    )
    op.create_check_constraint(
        "ck_compliance_plots_commodity_type",
        "compliance_plots",
        f"commodity_type IS NULL OR commodity_type IN {COMMODITY_VALUES}",
    )

    # compliance_records.commodity_type already exists (Text) in base schema;
    # legacy rows may have free-form values (cafe, cocoa_beans, coffee_green,
    # maiz, ...). Normalize BEFORE adding the CHECK so the migration doesn't
    # fail on existing data. Unknown values -> 'other'.
    op.execute(
        "UPDATE compliance_records SET commodity_type = CASE "
        "WHEN commodity_type IN ('coffee','cacao','palm','other') THEN commodity_type "
        "WHEN commodity_type IN ('cafe','coffee_green','coffee_parchment') THEN 'coffee' "
        "WHEN commodity_type IN ('cocoa','cocoa_beans','cocoa_nibs') THEN 'cacao' "
        "WHEN commodity_type IN ('palm_oil','cpo','ffb','palma') THEN 'palm' "
        "WHEN commodity_type IS NULL THEN NULL "
        "ELSE 'other' END"
    )
    op.create_check_constraint(
        "ck_compliance_records_commodity_type",
        "compliance_records",
        f"commodity_type IS NULL OR commodity_type IN {COMMODITY_VALUES}",
    )
    op.add_column(
        "compliance_records",
        sa.Column("cadmium_mg_per_kg", sa.Numeric(6, 3), nullable=True),
    )
    op.add_column(
        "compliance_records",
        sa.Column("cadmium_test_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "compliance_records",
        sa.Column("cadmium_test_lab", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "compliance_records",
        sa.Column("cadmium_test_doc_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "compliance_records",
        sa.Column("cadmium_eu_compliant", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "compliance_records",
        sa.Column("rspo_trace_model", sa.String(length=20), nullable=True),
    )
    op.create_check_constraint(
        "ck_compliance_records_rspo_trace_model",
        "compliance_records",
        f"rspo_trace_model IS NULL OR rspo_trace_model IN {RSPO_VALUES}",
    )

    # compliance_certificates.rspo_trace_model
    op.add_column(
        "compliance_certificates",
        sa.Column("rspo_trace_model", sa.String(length=20), nullable=True),
    )
    op.create_check_constraint(
        "ck_compliance_certificates_rspo_trace_model",
        "compliance_certificates",
        f"rspo_trace_model IS NULL OR rspo_trace_model IN {RSPO_VALUES}",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_compliance_certificates_rspo_trace_model",
        "compliance_certificates",
        type_="check",
    )
    op.drop_column("compliance_certificates", "rspo_trace_model")

    op.drop_constraint(
        "ck_compliance_records_rspo_trace_model",
        "compliance_records",
        type_="check",
    )
    op.drop_column("compliance_records", "rspo_trace_model")
    op.drop_column("compliance_records", "cadmium_eu_compliant")
    op.drop_column("compliance_records", "cadmium_test_doc_hash")
    op.drop_column("compliance_records", "cadmium_test_lab")
    op.drop_column("compliance_records", "cadmium_test_date")
    op.drop_column("compliance_records", "cadmium_mg_per_kg")
    op.drop_constraint(
        "ck_compliance_records_commodity_type",
        "compliance_records",
        type_="check",
    )

    op.drop_constraint(
        "ck_compliance_plots_commodity_type",
        "compliance_plots",
        type_="check",
    )
    op.drop_column("compliance_plots", "commodity_type")
