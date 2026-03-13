"""Add email_templates table, invitation/activation columns to users, new permissions

Revision ID: 004
Revises: 003
Create Date: 2026-03-03
"""
from __future__ import annotations

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = [
    ("email_templates", "email_templates.view",   "Ver plantillas de correo"),
    ("email_templates", "email_templates.manage", "Gestionar plantillas de correo"),
]

SEED_TEMPLATES = [
    {
        "slug": "user_invitation",
        "subject": "Bienvenido a $app_name — Activa tu cuenta",
        "description": "Se envía al invitar un nuevo usuario a la plataforma",
        "html_body": """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#1a1a1a">¡Hola $user_name!</h2>
<p>Has sido invitado a unirte a <strong>$app_name</strong>.</p>
<p>Haz clic en el siguiente enlace para activar tu cuenta y establecer tu contraseña:</p>
<p style="text-align:center;margin:30px 0">
  <a href="$link" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600">
    Activar mi cuenta
  </a>
</p>
<p style="color:#666;font-size:14px">Si no esperabas esta invitación, puedes ignorar este correo.</p>
<hr style="border:none;border-top:1px solid #eee;margin:30px 0">
<p style="color:#999;font-size:12px">$app_name</p>
</body></html>""",
    },
    {
        "slug": "password_reset",
        "subject": "Restablecer contraseña — $app_name",
        "description": "Se envía cuando un usuario solicita restablecer su contraseña",
        "html_body": """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#1a1a1a">Restablecer contraseña</h2>
<p>Hola $user_name,</p>
<p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en <strong>$app_name</strong>.</p>
<p style="text-align:center;margin:30px 0">
  <a href="$link" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600">
    Restablecer contraseña
  </a>
</p>
<p style="color:#666;font-size:14px">Este enlace expira en 1 hora. Si no solicitaste este cambio, ignora este correo.</p>
<hr style="border:none;border-top:1px solid #eee;margin:30px 0">
<p style="color:#999;font-size:12px">$app_name</p>
</body></html>""",
    },
    {
        "slug": "user_deactivated",
        "subject": "Tu cuenta ha sido desactivada — $app_name",
        "description": "Se envía cuando un administrador desactiva la cuenta de un usuario",
        "html_body": """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#1a1a1a">Cuenta desactivada</h2>
<p>Hola $user_name,</p>
<p>Tu cuenta en <strong>$app_name</strong> ha sido desactivada por un administrador.</p>
<p>Si crees que esto fue un error, contacta al administrador de tu organización.</p>
<hr style="border:none;border-top:1px solid #eee;margin:30px 0">
<p style="color:#999;font-size:12px">$app_name</p>
</body></html>""",
    },
]


def upgrade() -> None:
    # 1. Create email_templates table
    op.create_table(
        "email_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("html_body", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", "tenant_id", name="uq_email_templates_slug_tenant"),
    )
    op.create_index("ix_email_templates_tenant_id", "email_templates", ["tenant_id"])

    # 2. Add invitation/activation columns to users
    op.add_column("users", sa.Column("invitation_token", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("invitation_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("invitation_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("must_change_password", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.create_index("ix_users_invitation_token", "users", ["invitation_token"], unique=True)

    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # 3. Seed email templates for 'default' tenant
    for tpl in SEED_TEMPLATES:
        tpl_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO email_templates (id, tenant_id, slug, subject, html_body, description, is_active, created_at, updated_at) "
                "VALUES (:id, 'default', :slug, :subject, :html_body, :description, true, :now, :now)"
            ),
            {"id": tpl_id, "slug": tpl["slug"], "subject": tpl["subject"],
             "html_body": tpl["html_body"], "description": tpl["description"], "now": now},
        )

    # 4. Insert 2 new permissions
    for module, slug, name in NEW_PERMISSIONS:
        perm_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, name, slug, module, created_at) "
                "VALUES (:id, :name, :slug, :module, :created_at)"
                " ON CONFLICT (slug) DO NOTHING"
            ),
            {"id": perm_id, "name": name, "slug": slug, "module": module, "created_at": now},
        )

    # 5. Assign new permissions to all administrador roles
    rows = conn.execute(
        sa.text("SELECT id FROM permissions WHERE slug = ANY(:slugs)"),
        {"slugs": [s for _, s, _ in NEW_PERMISSIONS]},
    ).fetchall()
    actual_perm_ids = [r[0] for r in rows]

    role_rows = conn.execute(
        sa.text("SELECT id FROM roles WHERE slug = 'administrador'")
    ).fetchall()
    admin_role_ids = [r[0] for r in role_rows]

    for role_id in admin_role_ids:
        for perm_id in actual_perm_ids:
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:role_id, :perm_id) ON CONFLICT DO NOTHING"
                ),
                {"role_id": role_id, "perm_id": perm_id},
            )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove permissions
    slugs = [s for _, s, _ in NEW_PERMISSIONS]
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE slug = ANY(:slugs))"
        ),
        {"slugs": slugs},
    )
    conn.execute(
        sa.text("DELETE FROM permissions WHERE slug = ANY(:slugs)"),
        {"slugs": slugs},
    )

    # Remove user columns
    op.drop_index("ix_users_invitation_token", table_name="users")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "invitation_accepted_at")
    op.drop_column("users", "invitation_sent_at")
    op.drop_column("users", "invitation_token")

    # Remove email_templates
    op.drop_index("ix_email_templates_tenant_id", table_name="email_templates")
    op.drop_table("email_templates")
