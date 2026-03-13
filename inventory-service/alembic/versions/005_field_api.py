"""Drupal-inspired Field API: entity_bundles, field_storages, field_instances.

Revision ID: 005
Revises: 004
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

DEFAULT_TENANT = "default"


def _id() -> str:
    return str(uuid.uuid4())


def upgrade() -> None:
    # ─── 1. entity_bundles ────────────────────────────────────────────────

    op.create_table(
        "entity_bundles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "entity_type_id",
            sa.String(36),
            sa.ForeignKey("entity_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(20), nullable=True, server_default="#6366f1"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "tenant_id", "entity_type_id", "slug",
            name="uq_bundle_tenant_type_slug",
        ),
        sa.Index("ix_entity_bundles_tenant_id", "tenant_id"),
        sa.Index("ix_entity_bundles_entity_type_id", "entity_type_id"),
    )

    # ─── 2. field_storages ────────────────────────────────────────────────

    op.create_table(
        "field_storages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("field_type", sa.String(30), nullable=False, server_default="text"),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "settings",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint(
            "tenant_id", "field_name",
            name="uq_field_storage_tenant_name",
        ),
        sa.Index("ix_field_storages_tenant_id", "tenant_id"),
    )

    # ─── 3. field_instances ───────────────────────────────────────────────

    op.create_table(
        "field_instances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "field_storage_id",
            sa.String(36),
            sa.ForeignKey("field_storages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_type_id",
            sa.String(36),
            sa.ForeignKey("entity_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bundle_id",
            sa.String(36),
            sa.ForeignKey("entity_bundles.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("default_value", sa.Text, nullable=True),
        sa.Column(
            "validation_rules",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "display_settings",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint(
            "tenant_id", "field_storage_id", "entity_type_id", "bundle_id",
            name="uq_field_instance_storage_type_bundle",
        ),
        sa.Index("ix_field_instances_tenant_id", "tenant_id"),
        sa.Index("ix_field_instances_entity_type_id", "entity_type_id"),
        sa.Index("ix_field_instances_bundle_id", "bundle_id"),
        sa.Index("ix_field_instances_field_storage_id", "field_storage_id"),
    )

    # ─── 4. Add bundle_id to entities table ───────────────────────────────

    op.add_column(
        "entities",
        sa.Column(
            "bundle_id",
            sa.String(36),
            sa.ForeignKey("entity_bundles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ─── 5. Seed default field storages for the default tenant ────────────

    field_storages = sa.table(
        "field_storages",
        sa.column("id", sa.String),
        sa.column("tenant_id", sa.String),
        sa.column("field_name", sa.String),
        sa.column("field_type", sa.String),
        sa.column("label", sa.String),
        sa.column("description", sa.Text),
        sa.column("settings", postgresql.JSONB),
        sa.column("is_active", sa.Boolean),
    )

    # Seed a handful of commonly used field definitions
    seed_fields = [
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "brand",
            "field_type": "text",
            "label": "Marca",
            "description": "Marca o fabricante del producto",
            "settings": {"max_length": 100, "placeholder": "Ej: Samsung, Apple..."},
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "model",
            "field_type": "text",
            "label": "Modelo",
            "description": "Modelo o referencia del fabricante",
            "settings": {"max_length": 150},
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "weight_kg",
            "field_type": "decimal",
            "label": "Peso (kg)",
            "description": "Peso en kilogramos",
            "settings": {"min": 0, "precision": 3},
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "warranty_months",
            "field_type": "number",
            "label": "Garantía (meses)",
            "description": "Duración de la garantía en meses",
            "settings": {"min": 0, "max": 120},
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "expiration_date",
            "field_type": "date",
            "label": "Fecha de vencimiento",
            "description": "Fecha de expiración del producto",
            "settings": {},
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "is_fragile",
            "field_type": "boolean",
            "label": "Frágil",
            "description": "Indica si el producto requiere manejo especial",
            "settings": {"true_label": "Sí, es frágil", "false_label": "No"},
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "color",
            "field_type": "select",
            "label": "Color",
            "description": "Color principal del producto",
            "settings": {
                "options": [
                    {"value": "negro", "label": "Negro"},
                    {"value": "blanco", "label": "Blanco"},
                    {"value": "rojo", "label": "Rojo"},
                    {"value": "azul", "label": "Azul"},
                    {"value": "verde", "label": "Verde"},
                    {"value": "gris", "label": "Gris"},
                ],
                "allow_other": True,
            },
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "tags",
            "field_type": "multiselect",
            "label": "Etiquetas",
            "description": "Etiquetas para clasificación adicional",
            "settings": {
                "options": [
                    {"value": "importado", "label": "Importado"},
                    {"value": "nacional", "label": "Nacional"},
                    {"value": "premium", "label": "Premium"},
                    {"value": "oferta", "label": "En oferta"},
                    {"value": "nuevo", "label": "Nuevo"},
                ],
                "max_selections": 5,
            },
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "technical_specs",
            "field_type": "json",
            "label": "Especificaciones técnicas",
            "description": "Especificaciones técnicas en formato libre (JSON)",
            "settings": {},
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "notes",
            "field_type": "textarea",
            "label": "Notas",
            "description": "Notas o comentarios adicionales",
            "settings": {"max_length": 2000, "rows": 4},
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "manufacturer_url",
            "field_type": "url",
            "label": "URL del fabricante",
            "description": "Enlace a la página del fabricante",
            "settings": {"max_length": 2048},
            "is_active": True,
        },
        {
            "id": _id(),
            "tenant_id": DEFAULT_TENANT,
            "field_name": "contact_email",
            "field_type": "email",
            "label": "Email de contacto",
            "description": "Email del proveedor o contacto del producto",
            "settings": {},
            "is_active": True,
        },
    ]

    op.bulk_insert(field_storages, seed_fields)


def downgrade() -> None:
    op.drop_column("entities", "bundle_id")
    op.drop_table("field_instances")
    op.drop_table("field_storages")
    op.drop_table("entity_bundles")
