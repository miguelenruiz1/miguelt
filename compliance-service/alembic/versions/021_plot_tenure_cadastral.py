"""Add tenure, owner, producer and cadastral fields to compliance_plots.

EUDR Art. 8.2.f exige evidencia de "cualquier ley que confiera derechos a usar
la zona". Estos campos capturan al titular legal, al productor real (que puede
diferir del titular en arrendamientos/aparcerias), y la identificacion catastral
oficial — todo lo necesario para defender un DDS frente a una autoridad
competente europea.

Revision ID: 021_plot_tenure
Revises: 020_seed_cert_counter
"""
from alembic import op
import sqlalchemy as sa


revision = "021_plot_tenure"
down_revision = "020_seed_cert_counter"
branch_labels = None
depends_on = None


VALID_TENURE = (
    "owned",                  # propietario
    "leased",                 # arrendatario
    "sharecropped",           # aparceria / sociedad de hecho
    "concession",             # concesion
    "indigenous_collective",  # territorio colectivo indigena
    "afro_collective",        # territorio colectivo afrodescendiente
    "baldio_adjudicado",      # baldio adjudicado por la ANT
    "occupation",             # ocupacion / posesion sin titulo
    "other",
)


def upgrade() -> None:
    # Owner (titular legal del predio)
    op.add_column("compliance_plots", sa.Column("owner_name", sa.Text(), nullable=True))
    op.add_column("compliance_plots", sa.Column("owner_id_type", sa.Text(), nullable=True))
    op.add_column("compliance_plots", sa.Column("owner_id_number", sa.Text(), nullable=True))

    # Producer (quien efectivamente cultiva — puede ser el mismo owner o distinto)
    op.add_column("compliance_plots", sa.Column("producer_name", sa.Text(), nullable=True))
    op.add_column("compliance_plots", sa.Column("producer_id_type", sa.Text(), nullable=True))
    op.add_column("compliance_plots", sa.Column("producer_id_number", sa.Text(), nullable=True))

    # Cadastral identifier (folio matricula SNR / catastro multiproposito IGAC)
    op.add_column("compliance_plots", sa.Column("cadastral_id", sa.Text(), nullable=True))

    # Tenure type + dates (valida cobertura del derecho de uso)
    op.add_column("compliance_plots", sa.Column("tenure_type", sa.Text(), nullable=True))
    op.add_column("compliance_plots", sa.Column("tenure_start_date", sa.Date(), nullable=True))
    op.add_column("compliance_plots", sa.Column("tenure_end_date", sa.Date(), nullable=True))

    # Bandera para territorios indigenas/afro (Art. 10 — due diligence reforzado)
    op.add_column(
        "compliance_plots",
        sa.Column("indigenous_territory_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Constraint: tenure_type debe ser uno de los valores reconocidos cuando esta seteado
    valid_list = ",".join(f"'{t}'" for t in VALID_TENURE)
    op.create_check_constraint(
        "ck_compliance_plots_tenure_type",
        "compliance_plots",
        f"tenure_type IS NULL OR tenure_type IN ({valid_list})",
    )

    # Constraint: si ambas fechas estan, end >= start
    op.create_check_constraint(
        "ck_compliance_plots_tenure_dates",
        "compliance_plots",
        "tenure_start_date IS NULL OR tenure_end_date IS NULL OR tenure_end_date >= tenure_start_date",
    )

    # Indice para busquedas por catastro
    op.create_index(
        "ix_plots_cadastral",
        "compliance_plots",
        ["cadastral_id"],
        postgresql_where=sa.text("cadastral_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_plots_cadastral", table_name="compliance_plots")
    op.drop_constraint("ck_compliance_plots_tenure_dates", "compliance_plots", type_="check")
    op.drop_constraint("ck_compliance_plots_tenure_type", "compliance_plots", type_="check")
    for col in (
        "indigenous_territory_flag",
        "tenure_end_date",
        "tenure_start_date",
        "tenure_type",
        "cadastral_id",
        "producer_id_number",
        "producer_id_type",
        "producer_name",
        "owner_id_number",
        "owner_id_type",
        "owner_name",
    ):
        op.drop_column("compliance_plots", col)
