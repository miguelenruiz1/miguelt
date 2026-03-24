"""Create compliance_frameworks and tenant_framework_activations tables with EUDR seed.

Revision ID: 001_frameworks_and_activations
Revises: None
Create Date: 2026-03-21
"""
import json
import uuid
from datetime import date

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID

revision = "001_frameworks_and_activations"
down_revision = None
branch_labels = None
depends_on = None

EUDR_ID = "a0000000-0000-0000-0000-000000000001"

EUDR_VALIDATION_RULES = {
    "required_fields": [
        "hs_code", "commodity_type", "product_description",
        "quantity_kg", "country_of_production",
        "production_period_start", "production_period_end",
        "supplier_name", "supplier_address", "supplier_email",
        "deforestation_free_declaration", "legal_compliance_declaration",
    ],
    "required_if_export_eu": ["operator_eori"],
    "required_plots": True,
    "min_plots": 1,
    "plot_rules": {
        "requires_polygon_above_ha": 4,
        "coordinate_decimals": 6,
        "coordinate_system": "WGS84",
        "geojson_format": "EPSG-4326",
    },
    "commodity_specific": {
        "madera": {"required_fields": ["scientific_name"]},
        "wood": {"required_fields": ["scientific_name"]},
        "ganado_bovino": {"requires_establishments": True, "plot_type": "point_only"},
        "cattle": {"requires_establishments": True, "plot_type": "point_only"},
    },
    "risk_assessment": {
        "low_risk_countries": ["DE", "FR", "NL", "BE", "AT", "FI", "SE", "DK"],
        "high_risk_commodities": ["palm_oil", "soy", "cattle"],
        "simplified_dd_allowed_for_low_risk": True,
    },
    "cutoff_date": "2020-12-31",
    "retention_years": 5,
    "article_references": {
        "product_identification": "Art. 9(1)(a)-(b)",
        "geolocation": "Art. 9(1)(c)",
        "production_period": "Art. 9(1)(d)",
        "supply_chain": "Art. 9(1)(e)-(f)",
        "declarations": "Art. 9(1)(g)-(h)",
        "risk_assessment": "Art. 10-11",
        "risk_mitigation": "Art. 12",
    },
}


def upgrade() -> None:
    # ── compliance_frameworks ──
    op.create_table(
        "compliance_frameworks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("issuing_body", sa.Text(), nullable=True),
        sa.Column("target_markets", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("applicable_commodities", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("requires_geolocation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requires_dds", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requires_scientific_name", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("document_retention_years", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("cutoff_date", sa.Date(), nullable=True),
        sa.Column("legal_reference", sa.Text(), nullable=True),
        sa.Column("validation_rules", JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Text(), nullable=False, server_default="1.0"),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_frameworks_slug"),
    )

    # ── tenant_framework_activations ──
    op.create_table(
        "tenant_framework_activations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("framework_id", UUID(as_uuid=True), sa.ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("export_destination", ARRAY(sa.Text()), nullable=True),
        sa.Column("activated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("activated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("tenant_id", "framework_id", name="uq_tenant_framework"),
    )
    op.create_index("ix_tenant_framework_tenant", "tenant_framework_activations", ["tenant_id"])

    # ── Seed EUDR framework ──
    frameworks = sa.table(
        "compliance_frameworks",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("slug", sa.Text()),
        sa.column("name", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("issuing_body", sa.Text()),
        sa.column("target_markets", ARRAY(sa.Text())),
        sa.column("applicable_commodities", ARRAY(sa.Text())),
        sa.column("requires_geolocation", sa.Boolean()),
        sa.column("requires_dds", sa.Boolean()),
        sa.column("requires_scientific_name", sa.Boolean()),
        sa.column("document_retention_years", sa.Integer()),
        sa.column("cutoff_date", sa.Date()),
        sa.column("legal_reference", sa.Text()),
        sa.column("validation_rules", JSONB()),
        sa.column("is_active", sa.Boolean()),
        sa.column("version", sa.Text()),
    )

    op.bulk_insert(frameworks, [
        {
            "id": EUDR_ID,
            "slug": "eudr",
            "name": "EUDR — Reglamento (UE) 2023/1115",
            "description": (
                "Reglamento relativo a la comercialización en el mercado de la Unión "
                "de materias primas asociadas a la deforestación. Exige que operadores y "
                "comerciantes garanticen que productos colocados en el mercado UE sean libres "
                "de deforestación, producidos legalmente, y cubiertos por una declaración de "
                "diligencia debida (DDS)."
            ),
            "issuing_body": "European Union",
            "target_markets": ["EU", "EEA"],
            "applicable_commodities": [
                "ganado_bovino", "palma_aceitera", "cafe", "caucho", "madera", "soja", "cacao",
            ],
            "requires_geolocation": True,
            "requires_dds": True,
            "requires_scientific_name": False,
            "document_retention_years": 5,
            "cutoff_date": date(2020, 12, 31),
            "legal_reference": "Reglamento (UE) 2023/1115, Artículos 9-12, Anexo II",
            "validation_rules": EUDR_VALIDATION_RULES,
            "is_active": True,
            "version": "1.0",
        },
    ])


def downgrade() -> None:
    op.drop_index("ix_tenant_framework_tenant", table_name="tenant_framework_activations")
    op.drop_table("tenant_framework_activations")
    op.drop_table("compliance_frameworks")
