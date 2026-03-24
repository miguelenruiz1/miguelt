"""Seed subscription / billing email templates

Revision ID: 012
Revises: 011
Create Date: 2026-03-21
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ─── Template definitions ────────────────────────────────────────────────────

_BASE_STYLE = (
    "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; "
    "padding: 0; background: #ffffff;"
)

_HEADER = """
<div style="background: #10b981; padding: 28px 32px; border-radius: 8px 8px 0 0;">
  <h1 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: -0.3px;">
    TraceLog
  </h1>
</div>
""".strip()

_FOOTER = """
<div style="border-top: 1px solid #e5e7eb; padding: 20px 32px; text-align: center;">
  <p style="margin: 0; color: #9ca3af; font-size: 12px;">
    TraceLog &mdash; tracelog.co
  </p>
</div>
""".strip()

_CTA_BTN = (
    'style="display: inline-block; background: #10b981; color: #ffffff; '
    'padding: 14px 28px; border-radius: 6px; text-decoration: none; '
    'font-weight: 600; font-size: 15px;"'
)


def _wrap(inner_html: str) -> str:
    """Wrap content inside the standard email shell."""
    return (
        '<!DOCTYPE html>\n'
        '<html lang="es"><head><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1"></head>\n'
        f'<body style="{_BASE_STYLE}">\n'
        '<div style="border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">\n'
        f'{_HEADER}\n'
        '<div style="padding: 32px;">\n'
        f'{inner_html}\n'
        '</div>\n'
        f'{_FOOTER}\n'
        '</div>\n'
        '</body></html>'
    )


SEED_TEMPLATES = [
    # ── 1. Welcome ────────────────────────────────────────────────────────
    {
        "slug": "welcome",
        "subject": "Bienvenido a TraceLog",
        "description": "Se envia al activar la cuenta o el primer plan del tenant.",
        "html_body": _wrap(
            '<h2 style="margin: 0 0 16px; color: #111827; font-size: 20px;">'
            'Hola $user_name,</h2>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Tu cuenta en <strong>TraceLog</strong> esta lista. '
            'Desde ahora puedes gestionar tu cadena de custodia, inventario y '
            'cumplimiento normativo desde un solo lugar.</p>\n'
            '<p style="color: #374151; line-height: 1.6;">Estas son algunas cosas que puedes hacer:</p>\n'
            '<ul style="color: #374151; line-height: 1.8;">'
            '<li>Registrar activos y trazarlos en tiempo real</li>'
            '<li>Gestionar inventario y ordenes de compra</li>'
            '<li>Generar certificados de cumplimiento EUDR</li>'
            '</ul>\n'
            '<p style="text-align: center; margin: 28px 0;">'
            f'<a href="$dashboard_url" {_CTA_BTN}>Ir al dashboard</a></p>\n'
            '<p style="color: #6b7280; font-size: 13px;">'
            'Si tienes dudas, responde a este correo o visita nuestra '
            'seccion de ayuda.</p>'
        ),
    },
    # ── 2. Payment received ───────────────────────────────────────────────
    {
        "slug": "payment_received",
        "subject": "Pago recibido - TraceLog",
        "description": "Confirmacion de pago procesado exitosamente.",
        "html_body": _wrap(
            '<h2 style="margin: 0 0 16px; color: #111827; font-size: 20px;">'
            'Pago recibido</h2>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Hemos recibido tu pago correctamente. Aqui tienes el resumen:</p>\n'
            '<table style="width: 100%; border-collapse: collapse; margin: 20px 0;">'
            '<tr><td style="padding: 10px 0; color: #6b7280; border-bottom: 1px solid #f3f4f6;">'
            'Factura</td>'
            '<td style="padding: 10px 0; text-align: right; font-weight: 600; color: #111827; '
            'border-bottom: 1px solid #f3f4f6;">$invoice_number</td></tr>'
            '<tr><td style="padding: 10px 0; color: #6b7280; border-bottom: 1px solid #f3f4f6;">'
            'Monto</td>'
            '<td style="padding: 10px 0; text-align: right; font-weight: 600; color: #111827; '
            'border-bottom: 1px solid #f3f4f6;">$amount $currency</td></tr>'
            '<tr><td style="padding: 10px 0; color: #6b7280;">Periodo</td>'
            '<td style="padding: 10px 0; text-align: right; color: #111827;">$period</td></tr>'
            '</table>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Tu suscripcion sigue activa. Gracias por confiar en TraceLog.</p>'
        ),
    },
    # ── 3. Invoice generated ──────────────────────────────────────────────
    {
        "slug": "invoice_generated",
        "subject": "Tu factura TraceLog esta lista",
        "description": "Se envia cuando se genera una nueva factura pendiente de pago.",
        "html_body": _wrap(
            '<h2 style="margin: 0 0 16px; color: #111827; font-size: 20px;">'
            'Nueva factura disponible</h2>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Se ha generado una nueva factura para tu cuenta:</p>\n'
            '<table style="width: 100%; border-collapse: collapse; margin: 20px 0;">'
            '<tr><td style="padding: 10px 0; color: #6b7280; border-bottom: 1px solid #f3f4f6;">'
            'Factura</td>'
            '<td style="padding: 10px 0; text-align: right; font-weight: 600; color: #111827; '
            'border-bottom: 1px solid #f3f4f6;">$invoice_number</td></tr>'
            '<tr><td style="padding: 10px 0; color: #6b7280; border-bottom: 1px solid #f3f4f6;">'
            'Monto</td>'
            '<td style="padding: 10px 0; text-align: right; font-weight: 600; color: #111827; '
            'border-bottom: 1px solid #f3f4f6;">$amount $currency</td></tr>'
            '<tr><td style="padding: 10px 0; color: #6b7280;">Fecha limite</td>'
            '<td style="padding: 10px 0; text-align: right; color: #111827;">$due_date</td></tr>'
            '</table>\n'
            '<p style="text-align: center; margin: 28px 0;">'
            f'<a href="$pay_url" {_CTA_BTN}>Pagar ahora</a></p>\n'
            '<p style="color: #6b7280; font-size: 13px;">'
            'Si ya realizaste el pago, puedes ignorar este correo.</p>'
        ),
    },
    # ── 4. Trial ended ────────────────────────────────────────────────────
    {
        "slug": "trial_ended",
        "subject": "Tu periodo de prueba ha terminado",
        "description": "Se envia cuando expira el trial del tenant.",
        "html_body": _wrap(
            '<h2 style="margin: 0 0 16px; color: #111827; font-size: 20px;">'
            'Tu periodo de prueba finalizo</h2>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Hola $user_name,</p>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Tu periodo de prueba en <strong>TraceLog</strong> ha terminado. '
            'Para seguir disfrutando de todas las funcionalidades necesitas '
            'activar un plan.</p>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Sin un plan activo perderas acceso a:</p>\n'
            '<ul style="color: #374151; line-height: 1.8;">'
            '<li>Trazabilidad de activos y cadena de custodia</li>'
            '<li>Gestion de inventario y ordenes</li>'
            '<li>Reportes y certificados de cumplimiento</li>'
            '</ul>\n'
            '<p style="text-align: center; margin: 28px 0;">'
            f'<a href="$plans_url" {_CTA_BTN}>Ver planes</a></p>\n'
            '<p style="color: #6b7280; font-size: 13px;">'
            'Si necesitas mas tiempo, contactanos y te ayudamos.</p>'
        ),
    },
    # ── 5. Plan limit reached ─────────────────────────────────────────────
    {
        "slug": "plan_limit_reached",
        "subject": "Alcanzaste el limite de tu plan",
        "description": "Se envia cuando un recurso alcanza el limite del plan actual.",
        "html_body": _wrap(
            '<h2 style="margin: 0 0 16px; color: #111827; font-size: 20px;">'
            'Limite de plan alcanzado</h2>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Has alcanzado el limite de <strong>$resource</strong> en tu plan '
            '<strong>$plan_name</strong>.</p>\n'
            '<table style="width: 100%; border-collapse: collapse; margin: 20px 0;">'
            '<tr><td style="padding: 10px 0; color: #6b7280; border-bottom: 1px solid #f3f4f6;">'
            'Recurso</td>'
            '<td style="padding: 10px 0; text-align: right; font-weight: 600; color: #111827; '
            'border-bottom: 1px solid #f3f4f6;">$resource</td></tr>'
            '<tr><td style="padding: 10px 0; color: #6b7280; border-bottom: 1px solid #f3f4f6;">'
            'Uso actual</td>'
            '<td style="padding: 10px 0; text-align: right; font-weight: 600; color: #111827; '
            'border-bottom: 1px solid #f3f4f6;">$current</td></tr>'
            '<tr><td style="padding: 10px 0; color: #6b7280;">Limite del plan</td>'
            '<td style="padding: 10px 0; text-align: right; color: #111827;">$limit</td></tr>'
            '</table>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Para seguir creciendo, considera actualizar a un plan superior.</p>\n'
            '<p style="text-align: center; margin: 28px 0;">'
            f'<a href="$upgrade_url" {_CTA_BTN}>Actualizar plan</a></p>'
        ),
    },
    # ── 6. Certificate generated ──────────────────────────────────────────
    {
        "slug": "certificate_generated",
        "subject": "Certificado EUDR generado",
        "description": "Se envia cuando se genera un certificado de cumplimiento EUDR.",
        "html_body": _wrap(
            '<h2 style="margin: 0 0 16px; color: #111827; font-size: 20px;">'
            'Certificado EUDR generado</h2>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Se ha generado un nuevo certificado de cumplimiento para tu operacion:</p>\n'
            '<table style="width: 100%; border-collapse: collapse; margin: 20px 0;">'
            '<tr><td style="padding: 10px 0; color: #6b7280; border-bottom: 1px solid #f3f4f6;">'
            'No. Certificado</td>'
            '<td style="padding: 10px 0; text-align: right; font-weight: 600; color: #111827; '
            'border-bottom: 1px solid #f3f4f6;">$cert_number</td></tr>'
            '<tr><td style="padding: 10px 0; color: #6b7280;">Producto</td>'
            '<td style="padding: 10px 0; text-align: right; color: #111827;">$commodity</td></tr>'
            '</table>\n'
            '<p style="text-align: center; margin: 28px 0;">'
            f'<a href="$pdf_url" {_CTA_BTN}>Descargar PDF</a></p>\n'
            '<p style="color: #374151; line-height: 1.6;">'
            'Puedes verificar la autenticidad de este certificado en cualquier momento:</p>\n'
            '<p style="text-align: center; margin: 16px 0;">'
            '<a href="$verify_url" style="color: #10b981; font-weight: 600; '
            'text-decoration: underline;">Verificar certificado</a></p>'
        ),
    },
]


# ─── Migration ────────────────────────────────────────────────────────────────

def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    for tpl in SEED_TEMPLATES:
        tpl_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO email_templates "
                "(id, tenant_id, slug, subject, html_body, description, is_active, created_at, updated_at) "
                "VALUES (:id, 'default', :slug, :subject, :html_body, :description, true, :now, :now) "
                "ON CONFLICT ON CONSTRAINT uq_email_templates_slug_tenant DO NOTHING"
            ),
            {
                "id": tpl_id,
                "slug": tpl["slug"],
                "subject": tpl["subject"],
                "html_body": tpl["html_body"],
                "description": tpl["description"],
                "now": now,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    slugs = [t["slug"] for t in SEED_TEMPLATES]
    conn.execute(
        sa.text(
            "DELETE FROM email_templates WHERE tenant_id = 'default' AND slug = ANY(:slugs)"
        ),
        {"slugs": slugs},
    )
