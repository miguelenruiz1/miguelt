"""Authentication and seed service."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from app.core.role_templates import DEFAULT_TEMPLATES
from app.core.security import hash_password, verify_password
from app.core.settings import get_settings
from app.db.models import AuditLog, Role, User
from app.repositories.audit_repo import AuditRepository
from app.repositories.role_repo import RoleRepository
from app.repositories.user_repo import UserRepository
from app.services.email_service import EmailService

# ─── All permissions (seeded per-tenant on first registration) ────────────────
_PERMISSIONS = [
    # Administration
    ("admin",         "admin.users",              "Manage users"),
    ("admin",         "admin.roles",              "Manage roles"),
    ("admin",         "admin.audit",              "View audit logs"),
    # Logistics
    ("logistics",     "logistics.view",           "View logistics"),
    ("logistics",     "logistics.manage",         "Manage logistics"),
    # Inventory
    ("inventory",     "inventory.view",           "View inventory"),
    ("inventory",     "inventory.manage",         "Manage inventory"),
    ("inventory",     "inventory.config",         "Configure inventory"),
    # Subscription
    ("subscription",  "subscription.view",        "View subscription"),
    ("subscription",  "subscription.manage",      "Manage subscription"),
    # Email
    ("email",         "email.view",               "View email config"),
    ("email",         "email.manage",             "Manage email config"),
    # Integrations
    ("integrations",  "integrations.view",        "View integrations"),
    ("integrations",  "integrations.manage",      "Manage integrations"),
    # Reports
    ("reports",       "reports.view",             "View reports"),
    # Purchase Orders (granular)
    ("inventory",     "purchase_orders.view",      "Ver órdenes de compra"),
    ("inventory",     "purchase_orders.create",    "Crear órdenes de compra"),
    ("inventory",     "purchase_orders.edit",      "Editar órdenes de compra"),
    ("inventory",     "purchase_orders.delete",    "Eliminar órdenes de compra"),
    ("inventory",     "purchase_orders.send",      "Enviar OC al proveedor"),
    ("inventory",     "purchase_orders.confirm",   "Confirmar OC"),
    ("inventory",     "purchase_orders.cancel",    "Cancelar OC"),
    ("inventory",     "purchase_orders.receive",   "Recibir mercancía"),
    ("inventory",     "purchase_orders.approve",   "Aprobar órdenes de compra"),
    ("inventory",     "purchase_orders.view_cost", "Ver costos en OC"),
    ("inventory",     "purchase_orders.manage",    "Gestionar órdenes de compra"),
]


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.audit_repo = AuditRepository(db)

    async def register(
        self,
        *,
        email: str,
        username: str,
        full_name: str,
        password: str,
        tenant_id: str,
        phone: str | None = None,
        job_title: str | None = None,
        company: str | None = None,
    ) -> User:
        # Uniqueness checks
        if await self.user_repo.get_by_email(email):
            raise ConflictError(f"Email already registered: {email}")
        if await self.user_repo.get_by_username(username):
            raise ConflictError(f"Username already taken: {username}")

        # Seed roles/permissions for this tenant if not done yet
        await self._ensure_seeded(tenant_id)

        user = await self.user_repo.create(
            email=email,
            username=username,
            full_name=full_name,
            password_hash=hash_password(password),
            tenant_id=tenant_id,
            phone=phone,
            job_title=job_title,
            company=company,
        )

        # First active user gets admin role
        if await self.user_repo.count_active(tenant_id) == 1:
            admin_role = await self.role_repo.get_by_slug("administrador", tenant_id)
            if admin_role:
                await self.role_repo.assign_role_to_user(user.id, admin_role.id)

        await self.audit_repo.create(
            action="user.register",
            tenant_id=tenant_id,
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=user.id,
        )
        return user

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await self.user_repo.get_by_email(email)
        if not user:
            return None
        if not user.is_active:
            raise UnauthorizedError("Cuenta desactivada. Contacta al administrador.")
        if not user.password_hash or not verify_password(password, user.password_hash):
            return None
        return user

    async def invite_user(
        self,
        *,
        tenant_id: str,
        email: str,
        full_name: str,
        role_ids: list[str],
    ) -> User:
        """Create user without password and send invitation email."""
        if await self.user_repo.get_by_email(email):
            raise ConflictError(f"Email already registered: {email}")

        await self._ensure_seeded(tenant_id)

        # Generate username from email
        username = email.split("@")[0]
        base_username = username
        counter = 1
        while await self.user_repo.get_by_username(username):
            username = f"{base_username}{counter}"
            counter += 1

        token = secrets.token_urlsafe(64)
        now = datetime.now(timezone.utc)

        user = await self.user_repo.create(
            email=email,
            username=username,
            full_name=full_name,
            password_hash="",  # No password yet
            tenant_id=tenant_id,
            invitation_token=token,
            invitation_sent_at=now,
        )

        # Assign roles
        for role_id in role_ids:
            role = await self.role_repo.get_by_id(role_id)
            if role:
                await self.role_repo.assign_role_to_user(user.id, role.id)

        # Send invitation email
        settings = get_settings()
        link = f"{settings.FRONTEND_URL}/accept-invitation?token={token}"
        email_svc = EmailService()
        await email_svc.send_from_template(
            self.db, tenant_id, "user_invitation", email,
            {"user_name": full_name, "user_email": email,
             "link": link, "app_name": settings.APP_NAME},
        )

        await self.audit_repo.create(
            action="user.invite",
            tenant_id=tenant_id,
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=user.id,
        )
        return user

    async def resend_invitation(self, tenant_id: str, user_id: str) -> User:
        """Resend invitation email with a fresh token."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        if user.invitation_accepted_at:
            raise ValidationError("User has already accepted the invitation")

        token = secrets.token_urlsafe(64)
        now = datetime.now(timezone.utc)
        user = await self.user_repo.update(
            user, invitation_token=token, invitation_sent_at=now,
        )

        settings = get_settings()
        link = f"{settings.FRONTEND_URL}/accept-invitation?token={token}"
        email_svc = EmailService()
        await email_svc.send_from_template(
            self.db, tenant_id, "user_invitation", user.email,
            {"user_name": user.full_name, "user_email": user.email,
             "link": link, "app_name": settings.APP_NAME},
        )

        await self.audit_repo.create(
            action="user.resend_invitation",
            tenant_id=tenant_id,
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=user.id,
        )
        return user

    async def accept_invitation(self, token: str, password: str) -> User:
        """Accept invitation: set password and clear token."""
        user = await self.user_repo.get_by_invitation_token(token)
        if not user:
            raise ValidationError("Invalid or expired invitation token")

        now = datetime.now(timezone.utc)
        user = await self.user_repo.update(
            user,
            password_hash=hash_password(password),
            invitation_token=None,
            invitation_accepted_at=now,
        )

        await self.audit_repo.create(
            action="user.accept_invitation",
            tenant_id=user.tenant_id,
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=user.id,
        )
        return user

    async def request_password_reset(self, email: str, redis: aioredis.Redis) -> None:
        """Generate password reset token and send email. Always succeeds (no email leak)."""
        user = await self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            return  # Silent — don't reveal if email exists

        token = secrets.token_urlsafe(64)
        await redis.setex(f"pwd_reset:{token}", 3600, user.id)  # TTL 1h

        settings = get_settings()
        link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        email_svc = EmailService()
        await email_svc.send_from_template(
            self.db, user.tenant_id, "password_reset", user.email,
            {"user_name": user.full_name, "user_email": user.email,
             "link": link, "app_name": settings.APP_NAME},
        )

    async def reset_password(self, token: str, new_password: str, redis: aioredis.Redis) -> User:
        """Reset password using token from Redis."""
        user_id = await redis.get(f"pwd_reset:{token}")
        if not user_id:
            raise ValidationError("Invalid or expired reset token")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        user = await self.user_repo.update(user, password_hash=hash_password(new_password))
        await redis.delete(f"pwd_reset:{token}")

        await self.audit_repo.create(
            action="user.reset_password",
            tenant_id=user.tenant_id,
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=user.id,
        )
        return user

    async def deactivate_user(self, tenant_id: str, user_id: str, redis: aioredis.Redis) -> User:
        """Deactivate user, send notification, invalidate sessions."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        user = await self.user_repo.update(user, is_active=False)

        # Send deactivation email
        settings = get_settings()
        email_svc = EmailService()
        await email_svc.send_from_template(
            self.db, tenant_id, "user_deactivated", user.email,
            {"user_name": user.full_name, "user_email": user.email,
             "app_name": settings.APP_NAME},
        )

        # Invalidate all refresh tokens
        keys = await redis.keys(f"refresh:{user_id}:*")
        if keys:
            await redis.delete(*keys)

        # Invalidate cross-service caches
        await self._invalidate_user_cache(user_id)

        await self.audit_repo.create(
            action="user.deactivate",
            tenant_id=tenant_id,
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=user.id,
        )
        return user

    async def reactivate_user(self, tenant_id: str, user_id: str) -> User:
        """Reactivate a deactivated user."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        user = await self.user_repo.update(user, is_active=True)

        await self.audit_repo.create(
            action="user.reactivate",
            tenant_id=tenant_id,
            user_id=user.id,
            user_email=user.email,
            resource_type="user",
            resource_id=user.id,
        )
        return user

    async def get_permissions(self, user: User) -> set[str]:
        if user.is_superuser:
            # Superusers get all permissions
            perms = await self.role_repo.list_permissions()
            return {p.slug for p in perms}
        return await self.user_repo.get_user_permissions(user.id)

    async def get_roles(self, user: User) -> list[Role]:
        return await self.user_repo.get_user_roles(user.id)

    async def audit(
        self,
        *,
        action: str,
        tenant_id: str,
        user: User | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        return await self.audit_repo.create(
            action=action,
            tenant_id=tenant_id,
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def _invalidate_user_cache(user_id: str) -> None:
        """Invalidate cross-service caches for a user."""
        settings = get_settings()
        base_url = settings.REDIS_URL.rsplit("/", 1)[0]  # strip db number
        try:
            # subscription-service cache (db=3)
            r3 = aioredis.from_url(f"{base_url}/3", decode_responses=True)
            await r3.delete(f"sub_svc:me:{user_id}")
            await r3.aclose()
        except Exception:
            pass  # Best-effort

    async def _ensure_seeded(self, tenant_id: str) -> None:
        """Idempotently create all permissions and admin role for tenant.

        Always syncs the admin role permissions so new permissions added to
        _PERMISSIONS are picked up by existing tenants on next login/register.
        """
        perm_objects = []
        for module, slug, name in _PERMISSIONS:
            perm = await self.role_repo.get_or_create_permission(slug, module, name)
            perm_objects.append(perm)

        # Create or update admin role
        admin_role = await self.role_repo.get_by_slug("administrador", tenant_id)
        if not admin_role:
            admin_role = await self.role_repo.create(
                name="Administrador",
                slug="administrador",
                description="Full system access",
                is_system=True,
                tenant_id=tenant_id,
            )
        # Always sync permissions (handles new permissions added after initial seed)
        await self.role_repo.set_role_permissions(
            admin_role.id, [p.id for p in perm_objects]
        )

        # Seed default role templates into role_templates table
        from app.repositories.template_repo import TemplateRepository
        tmpl_repo = TemplateRepository(self.db)
        for tmpl in DEFAULT_TEMPLATES:
            existing = await tmpl_repo.get_by_slug(tmpl["slug"], tenant_id)
            if existing:
                continue
            await tmpl_repo.create(
                tenant_id=tenant_id,
                slug=tmpl["slug"],
                name=tmpl["name"],
                description=tmpl["description"],
                icon=tmpl["icon"],
                permissions=tmpl["permissions"],
                is_default=True,
            )
