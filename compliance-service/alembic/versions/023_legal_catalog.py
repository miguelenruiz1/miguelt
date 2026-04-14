"""Legal requirements catalog + per-plot compliance tracking.

MITECO webinar 3 (Alice Visa, EFI) established that EUDR legality assessment
must cover 6 ambitos, vary by country and commodity, and differ between
smallholder and industrial operations. This migration creates:

  - legal_requirement_catalogs: one per (country, commodity, version)
  - legal_requirements: the rules inside a catalog
  - plot_legal_compliance: per-plot status against each rule

A minimal seed for Colombia-cafe and Colombia-cacao is included so the
UI and tests have something to work with out of the box.

Revision ID: 023_legal_catalog
Revises: 022_plot_accuracy_scale
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "023_legal_catalog"
down_revision = "022_plot_accuracy_scale"
branch_labels = None
depends_on = None


AMBITOS = (
    "land_use_rights",               # Derechos de uso del suelo
    "environmental_protection",      # Proteccion del medio ambiente
    "labor_rights",                  # Derechos laborales
    "human_rights",                  # Derechos humanos
    "third_party_rights_fpic",       # Derechos de terceros + consentimiento libre previo informado
    "fiscal_customs_anticorruption", # Normativa fiscal, aduanera, anticorrupcion
)

APPLIES_TO_SCALE = (
    "all",                 # Aplica a smallholder + medium + industrial
    "smallholder",         # Solo <4 ha
    "medium",              # Solo 4-50 ha
    "industrial",          # Solo >50 ha
    "medium_or_industrial",# 4+ ha
)

COMPLIANCE_STATUS = (
    "satisfied",   # Evidencia cargada y valida
    "missing",     # Falta evidencia
    "na",          # No aplica a esta parcela
    "pending",     # En revision
)


def upgrade() -> None:
    # ---------- legal_requirement_catalogs ----------
    op.create_table(
        "legal_requirement_catalogs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("commodity", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("country_code", "commodity", "version", name="uq_legal_catalog_triple"),
    )
    op.create_index(
        "ix_legal_catalogs_country_commodity",
        "legal_requirement_catalogs",
        ["country_code", "commodity"],
    )

    # ---------- legal_requirements ----------
    op.create_table(
        "legal_requirements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "catalog_id",
            UUID(as_uuid=True),
            sa.ForeignKey("legal_requirement_catalogs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ambito", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("legal_reference", sa.Text(), nullable=True),
        sa.Column("applies_to_scale", sa.Text(), nullable=False, server_default="all"),
        sa.Column("required_document_type", sa.Text(), nullable=True),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("catalog_id", "code", name="uq_legal_requirement_code"),
        sa.CheckConstraint(
            "ambito IN ("
            + ",".join(f"'{a}'" for a in AMBITOS)
            + ")",
            name="ck_legal_requirements_ambito",
        ),
        sa.CheckConstraint(
            "applies_to_scale IN ("
            + ",".join(f"'{s}'" for s in APPLIES_TO_SCALE)
            + ")",
            name="ck_legal_requirements_scale",
        ),
    )
    op.create_index(
        "ix_legal_requirements_catalog",
        "legal_requirements",
        ["catalog_id"],
    )

    # ---------- plot_legal_compliance ----------
    op.create_table(
        "plot_legal_compliance",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "plot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("compliance_plots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requirement_id",
            UUID(as_uuid=True),
            sa.ForeignKey("legal_requirements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("evidence_media_id", UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("plot_id", "requirement_id", name="uq_plot_requirement"),
        sa.CheckConstraint(
            "status IN ("
            + ",".join(f"'{s}'" for s in COMPLIANCE_STATUS)
            + ")",
            name="ck_plot_legal_compliance_status",
        ),
    )
    op.create_index(
        "ix_plot_legal_compliance_plot",
        "plot_legal_compliance",
        ["plot_id"],
    )
    op.create_index(
        "ix_plot_legal_compliance_tenant",
        "plot_legal_compliance",
        ["tenant_id"],
    )

    # ---------- seed: Colombia — cafe + cacao ----------
    _seed_colombia_coffee_cacao()


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------
def _seed_colombia_coffee_cacao() -> None:
    """Minimal EUDR legal catalog for Colombia / cafe + cacao.

    Built from public sources: Ley 160/1994 (tierras), Ley 99/1993 (ambiental),
    CST (laboral), Ley 21/1991 (OIT 169 / FPIC), DIAN customs regs. This is a
    starting point — operators are expected to extend or replace it with a
    verified catalog (eg EFI, SAFE programme) before a real inspection.
    """
    catalogs = sa.table(
        "legal_requirement_catalogs",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("country_code", sa.Text()),
        sa.column("commodity", sa.Text()),
        sa.column("version", sa.Text()),
        sa.column("source", sa.Text()),
        sa.column("source_url", sa.Text()),
    )
    reqs = sa.table(
        "legal_requirements",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("catalog_id", UUID(as_uuid=True)),
        sa.column("ambito", sa.Text()),
        sa.column("code", sa.Text()),
        sa.column("title", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("legal_reference", sa.Text()),
        sa.column("applies_to_scale", sa.Text()),
        sa.column("required_document_type", sa.Text()),
        sa.column("is_blocking", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
    )

    def mk_reqs(catalog_id: uuid.UUID, commodity_label: str) -> list[dict]:
        return [
            # --- Derechos de uso del suelo ---
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="land_use_rights", code="CO-LUR-01",
                title="Titulo de propiedad o tenencia legal",
                description=(
                    f"Demostrar derecho legal de uso de la parcela donde se produce "
                    f"{commodity_label}: escritura publica, folio de matricula "
                    f"inmobiliaria, contrato de arrendamiento o acta de adjudicacion ANT."
                ),
                legal_reference="Ley 160/1994; Decreto 902/2017",
                applies_to_scale="all",
                required_document_type="land_title",
                is_blocking=True, sort_order=1,
            ),
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="land_use_rights", code="CO-LUR-02",
                title="Folio de matricula SNR / cedula catastral IGAC",
                description=(
                    "Identificacion catastral oficial de la parcela — requerida "
                    "en el DDS (Art. 8.2.f) para parcelas registradas."
                ),
                legal_reference="Resolucion 70/2011 IGAC",
                applies_to_scale="medium_or_industrial",
                required_document_type="cadastral_certificate",
                is_blocking=False, sort_order=2,
            ),
            # --- Proteccion del medio ambiente ---
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="environmental_protection", code="CO-ENV-01",
                title="Licencia ambiental (produccion industrial)",
                description=(
                    "Toda produccion agricola industrial requiere licencia ambiental "
                    "previa de la autoridad ambiental regional (CAR) cuando supera "
                    "los umbrales del Decreto 1076/2015."
                ),
                legal_reference="Ley 99/1993; Decreto 1076/2015",
                applies_to_scale="industrial",
                required_document_type="environmental_license",
                is_blocking=True, sort_order=3,
            ),
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="environmental_protection", code="CO-ENV-02",
                title="No interseccion con area protegida SINAP",
                description=(
                    "La parcela no debe estar dentro de un Parque Nacional Natural, "
                    "Reserva Forestal Protectora, DMI o similar del SINAP. "
                    "Verificable via geoportal RUNAP."
                ),
                legal_reference="Decreto 2372/2010 (SINAP)",
                applies_to_scale="all",
                required_document_type="protected_area_check",
                is_blocking=True, sort_order=4,
            ),
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="environmental_protection", code="CO-ENV-03",
                title="Uso legal de agroquimicos (ICA)",
                description=(
                    "Los insumos agricolas empleados deben estar registrados ante el "
                    "ICA. Evidencia: factura de compra con registro ICA visible."
                ),
                legal_reference="Decreto 1843/1991; Res. ICA 3028/2008",
                applies_to_scale="medium_or_industrial",
                required_document_type="ica_invoice",
                is_blocking=False, sort_order=5,
            ),
            # --- Derechos laborales ---
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="labor_rights", code="CO-LAB-01",
                title="Contratos laborales escritos",
                description=(
                    "Trabajadores permanentes deben contar con contrato laboral escrito "
                    "conforme al CST. Excluye mano de obra familiar de smallholders."
                ),
                legal_reference="CST Art. 22, 37, 39",
                applies_to_scale="medium_or_industrial",
                required_document_type="labor_contract",
                is_blocking=True, sort_order=6,
            ),
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="labor_rights", code="CO-LAB-02",
                title="Aportes a seguridad social (PILA)",
                description=(
                    "Planilla integrada de liquidacion de aportes (PILA) de los "
                    "ultimos 6 meses para todos los trabajadores."
                ),
                legal_reference="Ley 100/1993; Decreto 1670/2007",
                applies_to_scale="medium_or_industrial",
                required_document_type="pila_statement",
                is_blocking=True, sort_order=7,
            ),
            # --- Derechos humanos ---
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="human_rights", code="CO-HR-01",
                title="Declaracion de ausencia de trabajo infantil",
                description=(
                    "Declaracion jurada del productor + verificacion cruzada con "
                    "reportes municipales ICBF sobre trabajo infantil en la zona."
                ),
                legal_reference="Ley 1098/2006 (Codigo de Infancia y Adolescencia)",
                applies_to_scale="all",
                required_document_type="child_labor_affidavit",
                is_blocking=True, sort_order=8,
            ),
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="human_rights", code="CO-HR-02",
                title="Proteccion frente al uso de pesticidas",
                description=(
                    "Equipamiento de proteccion personal (EPP) + capacitacion "
                    "registrada. Obligatorio para produccion con agroquimicos."
                ),
                legal_reference="Res. 2400/1979 Mintrabajo; Dec. 1295/1994",
                applies_to_scale="medium_or_industrial",
                required_document_type="epp_training_record",
                is_blocking=False, sort_order=9,
            ),
            # --- Terceros / FPIC ---
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="third_party_rights_fpic", code="CO-FPIC-01",
                title="Consulta previa (cuando aplica)",
                description=(
                    "Si la parcela limita o se superpone con territorio colectivo "
                    "indigena o afrodescendiente, debe existir acta de consulta "
                    "previa con la comunidad segun Ley 21/1991 (OIT 169)."
                ),
                legal_reference="Ley 21/1991; Decreto 1320/1998",
                applies_to_scale="all",
                required_document_type="fpic_record",
                is_blocking=True, sort_order=10,
            ),
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="third_party_rights_fpic", code="CO-FPIC-02",
                title="Estudio de impacto ambiental y social (EIA)",
                description=(
                    "Produccion industrial que afecta comunidades vecinas debe contar "
                    "con EIA aprobado que incluya el componente social."
                ),
                legal_reference="Decreto 1076/2015 Titulo 2",
                applies_to_scale="industrial",
                required_document_type="eia_report",
                is_blocking=True, sort_order=11,
            ),
            # --- Fiscal / aduanero / anticorrupcion ---
            dict(
                id=uuid.uuid4(), catalog_id=catalog_id,
                ambito="fiscal_customs_anticorruption", code="CO-FCA-01",
                title="RUT activo del productor",
                description=(
                    "Registro Unico Tributario (DIAN) vigente del productor o "
                    "asociacion productora."
                ),
                legal_reference="Estatuto Tributario; Res. DIAN 139/2012",
                applies_to_scale="all",
                required_document_type="rut",
                is_blocking=False, sort_order=12,
            ),
        ]

    catalog_rows = []
    all_req_rows = []

    for commodity, commodity_label in (("coffee", "cafe"), ("cocoa", "cacao")):
        cat_id = uuid.uuid4()
        catalog_rows.append(
            dict(
                id=cat_id,
                country_code="CO",
                commodity=commodity,
                version="2026.04-eudr-v1",
                source="Trace internal draft — EFI/SAFE-style mapping",
                source_url=None,
            )
        )
        all_req_rows.extend(mk_reqs(cat_id, commodity_label))

    op.bulk_insert(catalogs, catalog_rows)
    op.bulk_insert(reqs, all_req_rows)


def downgrade() -> None:
    op.drop_index("ix_plot_legal_compliance_tenant", table_name="plot_legal_compliance")
    op.drop_index("ix_plot_legal_compliance_plot", table_name="plot_legal_compliance")
    op.drop_table("plot_legal_compliance")
    op.drop_index("ix_legal_requirements_catalog", table_name="legal_requirements")
    op.drop_table("legal_requirements")
    op.drop_index(
        "ix_legal_catalogs_country_commodity", table_name="legal_requirement_catalogs"
    )
    op.drop_table("legal_requirement_catalogs")
