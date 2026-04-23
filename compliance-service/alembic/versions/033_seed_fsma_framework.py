"""Seed FSMA Rule 204 (USA Food Traceability Final Rule) en compliance_frameworks.

Revision ID: 033_seed_fsma_framework
Revises: 032_dds_polling_fields
Create Date: 2026-04-22

Agrega el framework FSMA Rule 204 (Food Safety Modernization Act — Food
Traceability Final Rule, 21 CFR Part 1 Subpart S) para que los tenants
puedan activarlo y emitir registros de trazabilidad para exportación a
EEUU.

Contexto:
- La FDA no tiene portal de submisión tipo TRACES NT (EUDR) — el modelo
  FSMA es "mantené registros electrónicos y entregálos dentro de 24 h
  cuando FDA los pida".
- Por eso FSMA NO requiere DDS (requires_dds=False) pero SÍ retención de
  2 años de records (vs 5 de EUDR).
- Aplica solo a productos de la Food Traceability List (FTL). Los
  tenants cuyo producto no está en la FTL pueden ignorar este framework.
- Las Critical Tracking Events (CTE) mapean 1:1 a los eventos de
  custodia que ya registramos (growing=CREATED, shipping=HANDOFF,
  receiving=ARRIVED, transformation=PROCESSED, etc.).
"""
import uuid
from datetime import date
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID


revision = "033_seed_fsma_framework"
down_revision = "032_dds_polling_fields"
branch_labels = None
depends_on = None


FSMA_ID = "a0000000-0000-0000-0000-000000000002"

FSMA_VALIDATION_RULES = {
    # Campos mínimos del registro de trazabilidad FSMA
    "required_fields": [
        "traceability_lot_code",         # TLC — Rule 204 § 1.1320
        "commodity_type",
        "product_description",
        "quantity_kg",                   # o unidad equivalente
        "unit_of_measure",
        "country_of_production",
        "date_of_harvest_or_creation",
        "shipper_name",
        "shipper_address",
        "receiver_name",
        "receiver_address",
        "reference_document_type",       # BOL, PO, invoice
        "reference_document_number",
    ],
    # Para exportación formal a USA, el operador local (importer of record)
    # necesita ser registrado en FDA y tener un Unique Facility Identifier.
    "required_if_export_us": ["fda_facility_id"],
    # Critical Tracking Events — mapeo al dominio de Trace (custody_events)
    "critical_tracking_events": [
        {"cte": "growing",        "trace_event": "CREATED"},
        {"cte": "receiving",      "trace_event": "ARRIVED"},
        {"cte": "transformation", "trace_event": "PROCESSED"},
        {"cte": "creation",       "trace_event": "LOADED"},
        {"cte": "shipping",       "trace_event": "HANDOFF"},
    ],
    # Food Traceability List (FTL) — solo estos productos caen bajo Rule 204.
    # Otras commodities pueden usar FSMA para trazabilidad voluntaria pero
    # no es obligatoria.
    "food_traceability_list": [
        "leafy_greens", "melons", "tropical_tree_fruits", "fresh_herbs",
        "cucumbers", "tomatoes", "peppers", "sprouts", "fresh_cut_produce",
        "shell_eggs", "nut_butters", "fresh_soft_cheeses",
        "ready_to_eat_deli_salads", "finfish", "crustaceans", "mollusks",
    ],
    # Retención según 21 CFR § 1.1455
    "retention_years": 2,
    # Ventana de respuesta a solicitud FDA
    "fda_response_window_hours": 24,
    # Referencia legal
    "article_references": {
        "tlc": "21 CFR § 1.1320",
        "required_records": "21 CFR § 1.1330 — § 1.1345",
        "shipping_kde": "21 CFR § 1.1340",
        "receiving_kde": "21 CFR § 1.1345",
        "retention": "21 CFR § 1.1455",
        "response_window": "21 CFR § 1.1455(c)",
    },
    # Campos específicos opcionales que el tenant puede capturar
    "optional_fields": [
        "growing_area_coordinates",      # para leafy greens, tomatoes, etc.
        "harvest_date",
        "cooling_location",
        "first_land_based_receiver",     # para seafood
        "catch_area_fao",                # para seafood
    ],
}


def upgrade() -> None:
    # Idempotent insert: si alguien ya seedeó manualmente o lo estan
    # corriendo dos veces contra la misma DB, no falla.
    bind = op.get_bind()
    existing = bind.execute(
        sa.text("SELECT 1 FROM compliance_frameworks WHERE slug = 'fsma_204' LIMIT 1")
    ).first()
    if existing:
        return

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
            "id": FSMA_ID,
            "slug": "fsma_204",
            "name": "FSMA Rule 204 — Food Traceability Final Rule (USA)",
            "description": (
                "Food Safety Modernization Act, Rule 204 — regla final de "
                "trazabilidad alimentaria de la FDA. Exige registros "
                "electronicos de Critical Tracking Events (growing, "
                "receiving, transformation, creation, shipping) con Key "
                "Data Elements (TLC, cantidad, ubicacion, fechas, remitente/"
                "receptor) para productos de la Food Traceability List. FDA "
                "puede requerirlos dentro de 24 horas."
            ),
            "issuing_body": "U.S. Food & Drug Administration (FDA)",
            "target_markets": ["US"],
            "applicable_commodities": [
                "leafy_greens", "melones", "frutas_tropicales", "hierbas_frescas",
                "pepinos", "tomates", "pimientos", "brotes",
                "huevos", "mantequillas_frutos_secos", "quesos_frescos",
                "ensaladas_listas", "pescado", "crustaceos", "moluscos",
            ],
            "requires_geolocation": False,  # solo para growing area de leafy greens
            "requires_dds": False,          # FDA no tiene portal tipo TRACES
            "requires_scientific_name": False,
            "document_retention_years": 2,
            "cutoff_date": None,  # no hay cutoff de deforestacion
            "legal_reference": "21 CFR Part 1, Subpart S (§§ 1.1300–1.1455)",
            "validation_rules": FSMA_VALIDATION_RULES,
            "is_active": True,
            "version": "1.0",
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM compliance_frameworks WHERE slug = 'fsma_204'")
