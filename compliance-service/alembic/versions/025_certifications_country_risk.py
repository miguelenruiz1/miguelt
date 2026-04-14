"""Certification scheme credibility scoring + country risk benchmarks.

Two independent but related tables:

  - certification_schemes: registry of certification schemes (Rainforest
    Alliance, FSC, MSPO, UTZ, 4C, Fairtrade, etc.) with a credibility score
    across 4 axes (ownership, transparency, audit independence, grievance
    mechanism). Score 0-3 per axis, 0-12 total. Aliases MITECO webinar 3
    (Alice, EFI) credibility criteria.

  - country_risk_benchmarks: per-country static benchmark with CPI score,
    conflict flag, deforestation prevalence, overall risk level. Seed uses
    public sources (Transparency International CPI 2024, ACLED, GFW).

Revision ID: 025_cert_country_risk
Revises: 024_legal_catalogs_extra
"""
from __future__ import annotations

import uuid
from datetime import date

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "025_cert_country_risk"
down_revision = "024_legal_catalogs_extra"
branch_labels = None
depends_on = None


SCOPE_OPTIONS = ("legality", "chain_of_custody", "sustainability", "full")
SCHEME_TYPES = ("commodity_specific", "generic", "national")


def upgrade() -> None:
    # ---------- certification_schemes ----------
    op.create_table(
        "certification_schemes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("scheme_type", sa.Text(), nullable=False, server_default="generic"),
        sa.Column("scope", sa.Text(), nullable=False, server_default="full"),
        sa.Column("commodities", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("ownership_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transparency_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("audit_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grievance_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("covers_eudr_ambitos", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("reference_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "scope IN ('legality','chain_of_custody','sustainability','full')",
            name="ck_certification_schemes_scope",
        ),
        sa.CheckConstraint(
            "scheme_type IN ('commodity_specific','generic','national')",
            name="ck_certification_schemes_type",
        ),
        sa.CheckConstraint(
            "ownership_score BETWEEN 0 AND 3 AND "
            "transparency_score BETWEEN 0 AND 3 AND "
            "audit_score BETWEEN 0 AND 3 AND "
            "grievance_score BETWEEN 0 AND 3",
            name="ck_certification_schemes_scores_range",
        ),
    )
    op.create_index("ix_certification_schemes_slug", "certification_schemes", ["slug"])

    # ---------- country_risk_benchmarks ----------
    op.create_table(
        "country_risk_benchmarks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.Text(), nullable=False),
        sa.Column("cpi_score", sa.Integer(), nullable=True),
        sa.Column("cpi_rank", sa.Integer(), nullable=True),
        sa.Column("conflict_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deforestation_prevalence", sa.Text(), nullable=True),
        sa.Column("indigenous_risk_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "risk_level IN ('negligible','low','standard','high','critical')",
            name="ck_country_risk_level",
        ),
        sa.CheckConstraint(
            "cpi_score IS NULL OR (cpi_score BETWEEN 0 AND 100)",
            name="ck_country_risk_cpi_range",
        ),
        sa.CheckConstraint(
            "deforestation_prevalence IS NULL OR deforestation_prevalence IN "
            "('very_low','low','medium','high','very_high')",
            name="ck_country_risk_def_prevalence",
        ),
    )
    op.create_index(
        "ix_country_risk_current",
        "country_risk_benchmarks",
        ["country_code"],
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_unique_constraint(
        "uq_country_risk_current",
        "country_risk_benchmarks",
        ["country_code", "as_of_date"],
    )

    _seed_certification_schemes()
    _seed_country_benchmarks()


# ---------------------------------------------------------------------------
# Seeds
# ---------------------------------------------------------------------------
def _seed_certification_schemes() -> None:
    """Initial catalog of 6 recognised certification schemes.

    Scores are preliminary and reflect publicly-available information on each
    scheme's governance. Operators should update them based on their own due
    diligence (MITECO webinar 3 — Alice Visa).
    """
    tbl = sa.table(
        "certification_schemes",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("slug", sa.Text()),
        sa.column("name", sa.Text()),
        sa.column("scheme_type", sa.Text()),
        sa.column("scope", sa.Text()),
        sa.column("commodities", JSONB),
        sa.column("ownership_score", sa.Integer()),
        sa.column("transparency_score", sa.Integer()),
        sa.column("audit_score", sa.Integer()),
        sa.column("grievance_score", sa.Integer()),
        sa.column("total_score", sa.Integer()),
        sa.column("covers_eudr_ambitos", JSONB),
        sa.column("reference_url", sa.Text()),
        sa.column("notes", sa.Text()),
    )
    rows = [
        # Rainforest Alliance
        dict(
            id=uuid.uuid4(),
            slug="rainforest-alliance",
            name="Rainforest Alliance Certified (2020 standard)",
            scheme_type="generic", scope="sustainability",
            commodities=["coffee", "cocoa", "tea", "banana"],
            ownership_score=3, transparency_score=2, audit_score=2, grievance_score=2,
            total_score=9,
            covers_eudr_ambitos=[
                "environmental_protection", "labor_rights", "human_rights"
            ],
            reference_url="https://www.rainforest-alliance.org/business/certification/",
            notes=(
                "Amplia cobertura de practicas ambientales y sociales. No cubre "
                "plenamente el ambito de derechos de uso de suelo ni el fiscal."
            ),
        ),
        # FSC (madera)
        dict(
            id=uuid.uuid4(),
            slug="fsc",
            name="Forest Stewardship Council (FSC) FM + CoC",
            scheme_type="generic", scope="full",
            commodities=["wood", "rubber"],
            ownership_score=3, transparency_score=3, audit_score=3, grievance_score=3,
            total_score=12,
            covers_eudr_ambitos=[
                "land_use_rights", "environmental_protection", "labor_rights",
                "human_rights", "third_party_rights_fpic"
            ],
            reference_url="https://fsc.org/en",
            notes=(
                "Ref. del sector forestal. Gobernanza tripartita (ambiental, "
                "social, economica). Alta credibilidad segun criterios MITECO."
            ),
        ),
        # 4C
        dict(
            id=uuid.uuid4(),
            slug="4c",
            name="4C (Common Code for the Coffee Community)",
            scheme_type="commodity_specific", scope="sustainability",
            commodities=["coffee"],
            ownership_score=2, transparency_score=2, audit_score=2, grievance_score=1,
            total_score=7,
            covers_eudr_ambitos=["environmental_protection", "labor_rights"],
            reference_url="https://www.4c-services.org/",
            notes=(
                "Umbral de entrada del sector cafe. Baseline util pero no "
                "cubre plenamente derechos humanos ni mecanismo de quejas."
            ),
        ),
        # UTZ (absorbido por Rainforest Alliance, legacy)
        dict(
            id=uuid.uuid4(),
            slug="utz-legacy",
            name="UTZ (legacy — migrado a Rainforest Alliance)",
            scheme_type="generic", scope="sustainability",
            commodities=["coffee", "cocoa", "tea"],
            ownership_score=2, transparency_score=2, audit_score=2, grievance_score=1,
            total_score=7,
            covers_eudr_ambitos=["environmental_protection", "labor_rights"],
            reference_url="https://utz.org/",
            notes=(
                "Scheme fusionado con Rainforest Alliance en 2018. Los sellos "
                "UTZ historicos siguen siendo aceptables como evidencia parcial."
            ),
        ),
        # Fairtrade
        dict(
            id=uuid.uuid4(),
            slug="fairtrade",
            name="Fairtrade International (FLO)",
            scheme_type="generic", scope="sustainability",
            commodities=["coffee", "cocoa", "banana", "sugar", "tea"],
            ownership_score=3, transparency_score=3, audit_score=2, grievance_score=2,
            total_score=10,
            covers_eudr_ambitos=["labor_rights", "human_rights", "environmental_protection"],
            reference_url="https://www.fairtrade.net/",
            notes=(
                "Fuerte en dimension social/laboral y remuneracion minima. "
                "Menor enfoque en derechos de uso de suelo que FSC."
            ),
        ),
        # MSPO (Malasia)
        dict(
            id=uuid.uuid4(),
            slug="mspo",
            name="Malaysian Sustainable Palm Oil (MSPO)",
            scheme_type="national", scope="sustainability",
            commodities=["palm_oil"],
            ownership_score=1, transparency_score=2, audit_score=2, grievance_score=1,
            total_score=6,
            covers_eudr_ambitos=["environmental_protection", "labor_rights"],
            reference_url="https://www.mpocc.org.my/",
            notes=(
                "Certificacion obligatoria del gobierno malasio para palma. "
                "Dashboard publico con geolocalizacion. No tiene CoC propia — "
                "eso lo provee MTCS. Governance dominada por actores nacionales."
            ),
        ),
    ]
    op.bulk_insert(tbl, rows)


def _seed_country_benchmarks() -> None:
    """Static country risk seed (as of 2026-04-11).

    Sources:
      - CPI: Transparency International Corruption Perceptions Index 2024
      - Deforestation: Global Forest Watch Primary Forest Loss 2023
      - Conflict: ACLED global country flags

    These values are intentionally static so the system has a baseline even
    without the (future) cron job. Operators can override via admin API.
    """
    tbl = sa.table(
        "country_risk_benchmarks",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("country_code", sa.Text()),
        sa.column("risk_level", sa.Text()),
        sa.column("cpi_score", sa.Integer()),
        sa.column("cpi_rank", sa.Integer()),
        sa.column("conflict_flag", sa.Boolean()),
        sa.column("deforestation_prevalence", sa.Text()),
        sa.column("indigenous_risk_flag", sa.Boolean()),
        sa.column("notes", sa.Text()),
        sa.column("source", sa.Text()),
        sa.column("as_of_date", sa.Date()),
    )
    today = date(2026, 4, 11)
    rows = [
        dict(
            id=uuid.uuid4(), country_code="CO", risk_level="standard",
            cpi_score=39, cpi_rank=92, conflict_flag=True,
            deforestation_prevalence="medium", indigenous_risk_flag=True,
            notes=(
                "Colombia — alta deforestacion en la Amazonia colombiana "
                "(Caqueta, Guaviare). Zonas rojas ACLED en Pacifico y Bajo "
                "Cauca. Due diligence estandar, reforzado cerca de parques "
                "nacionales y territorios etnicos."
            ),
            source="TI CPI 2024 + GFW 2023 + ACLED 2024",
            as_of_date=today,
        ),
        dict(
            id=uuid.uuid4(), country_code="PE", risk_level="high",
            cpi_score=34, cpi_rank=121, conflict_flag=False,
            deforestation_prevalence="high", indigenous_risk_flag=True,
            notes=(
                "Peru — alta perdida de bosque primario en Ucayali, Madre "
                "de Dios y Amazonas. Riesgo alto por mineria ilegal y "
                "conflictos con comunidades nativas."
            ),
            source="TI CPI 2024 + GFW 2023 + MINAM",
            as_of_date=today,
        ),
        dict(
            id=uuid.uuid4(), country_code="EC", risk_level="standard",
            cpi_score=34, cpi_rank=121, conflict_flag=False,
            deforestation_prevalence="medium", indigenous_risk_flag=True,
            notes=(
                "Ecuador — SNAP protege ~20% del territorio. Presion en "
                "frontera amazonica. Debida diligencia estandar; reforzar "
                "si la parcela esta en Sucumbios/Orellana."
            ),
            source="TI CPI 2024 + MAATE + GFW 2023",
            as_of_date=today,
        ),
        dict(
            id=uuid.uuid4(), country_code="BR", risk_level="high",
            cpi_score=34, cpi_rank=107, conflict_flag=False,
            deforestation_prevalence="very_high", indigenous_risk_flag=True,
            notes=(
                "Brasil — Amazonia Legal y Cerrado concentran la mayor "
                "perdida de bosque primario del mundo. Lista suja IBAMA y "
                "MTE deben cruzarse obligatoriamente."
            ),
            source="TI CPI 2024 + PRODES 2024 + GFW 2023",
            as_of_date=today,
        ),
        dict(
            id=uuid.uuid4(), country_code="CI", risk_level="high",
            cpi_score=40, cpi_rank=87, conflict_flag=False,
            deforestation_prevalence="very_high", indigenous_risk_flag=False,
            notes=(
                "Cote d'Ivoire — el ~80% del bosque original se perdio "
                "desde 1960. Cacao frecuentemente cultivado en forets "
                "classees. Due diligence reforzado obligatorio."
            ),
            source="TI CPI 2024 + SODEFOR + GFW 2023",
            as_of_date=today,
        ),
        dict(
            id=uuid.uuid4(), country_code="GH", risk_level="standard",
            cpi_score=42, cpi_rank=80, conflict_flag=False,
            deforestation_prevalence="high", indigenous_risk_flag=False,
            notes=(
                "Ghana — similar a Cote d'Ivoire pero con mejor gobernanza "
                "forestal. Existen parcelas cacaoteras legalmente admitidas "
                "dentro de forest reserves — cruzar con lista del Forestry "
                "Commission."
            ),
            source="TI CPI 2024 + Forestry Commission GH + GFW 2023",
            as_of_date=today,
        ),
        dict(
            id=uuid.uuid4(), country_code="ID", risk_level="high",
            cpi_score=37, cpi_rank=99, conflict_flag=False,
            deforestation_prevalence="very_high", indigenous_risk_flag=True,
            notes=(
                "Indonesia — palma de aceite, conversion de turberas. "
                "Requiere cruce con ISPO + KLHK + mapas de concesiones."
            ),
            source="TI CPI 2024 + KLHK + GFW 2023",
            as_of_date=today,
        ),
        dict(
            id=uuid.uuid4(), country_code="MY", risk_level="standard",
            cpi_score=50, cpi_rank=57, conflict_flag=False,
            deforestation_prevalence="high", indigenous_risk_flag=True,
            notes=(
                "Malasia — produccion de palma con certificacion MSPO "
                "obligatoria. Dashboard publico ayuda a cruzar parcelas, "
                "pero faltan mecanismos de trazabilidad fuertes."
            ),
            source="TI CPI 2024 + MPOCC + GFW 2023",
            as_of_date=today,
        ),
    ]
    op.bulk_insert(tbl, rows)


def downgrade() -> None:
    op.drop_constraint("uq_country_risk_current", "country_risk_benchmarks", type_="unique")
    op.drop_index("ix_country_risk_current", table_name="country_risk_benchmarks")
    op.drop_table("country_risk_benchmarks")
    op.drop_index("ix_certification_schemes_slug", table_name="certification_schemes")
    op.drop_table("certification_schemes")
