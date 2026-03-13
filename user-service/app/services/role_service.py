"""Role management service."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.db.models import Permission, Role, RoleTemplate
from app.repositories.role_repo import RoleRepository
from app.repositories.template_repo import TemplateRepository


class RoleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.role_repo = RoleRepository(db)
        self.tmpl_repo = TemplateRepository(db)

    # ── Roles ─────────────────────────────────────────────────────────────────

    async def list(self, tenant_id: str) -> list[Role]:
        return await self.role_repo.list(tenant_id)

    async def get(self, role_id: str) -> Role:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role {role_id} not found")
        return role

    async def create(self, *, name: str, slug: str, description: str | None, tenant_id: str) -> Role:
        existing = await self.role_repo.get_by_slug(slug, tenant_id)
        if existing:
            raise ConflictError(f"Role slug '{slug}' already exists in this tenant")
        return await self.role_repo.create(
            name=name, slug=slug, description=description, tenant_id=tenant_id
        )

    async def update(self, role_id: str, **kwargs) -> Role:
        role = await self.get(role_id)
        return await self.role_repo.update(role, **kwargs)

    async def delete(self, role_id: str) -> None:
        role = await self.get(role_id)
        if role.is_system:
            raise ForbiddenError("System roles cannot be deleted")
        await self.role_repo.delete(role)

    async def list_permissions(self) -> list[Permission]:
        return await self.role_repo.list_permissions()

    async def get_role_permissions(self, role_id: str) -> list[Permission]:
        await self.get(role_id)  # ensure exists
        return await self.role_repo.get_role_permissions(role_id)

    async def set_role_permissions(self, role_id: str, perm_ids: list[str]) -> None:
        role = await self.get(role_id)
        await self.role_repo.set_role_permissions(role.id, perm_ids)

    # ── Templates ─────────────────────────────────────────────────────────────

    async def list_templates(self, tenant_id: str) -> list[RoleTemplate]:
        return await self.tmpl_repo.list(tenant_id)

    async def get_template(self, template_id: str) -> RoleTemplate:
        tmpl = await self.tmpl_repo.get_by_id(template_id)
        if not tmpl:
            raise NotFoundError(f"Template {template_id} not found")
        return tmpl

    async def create_template(
        self,
        *,
        tenant_id: str,
        name: str,
        slug: str,
        description: str | None,
        icon: str,
        permissions: list[str],
    ) -> RoleTemplate:
        existing = await self.tmpl_repo.get_by_slug(slug, tenant_id)
        if existing:
            raise ConflictError(f"Template slug '{slug}' already exists")
        return await self.tmpl_repo.create(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            description=description,
            icon=icon,
            permissions=permissions,
        )

    async def update_template(self, template_id: str, **kwargs) -> RoleTemplate:
        tmpl = await self.get_template(template_id)
        return await self.tmpl_repo.update(tmpl, **kwargs)

    async def delete_template(self, template_id: str) -> None:
        tmpl = await self.get_template(template_id)
        await self.tmpl_repo.delete(tmpl)

    async def create_from_template(self, tenant_id: str, template_id: str) -> Role:
        """Create a new editable role from a template's permissions."""
        tmpl = await self.get_template(template_id)

        # Find a unique slug (append -2, -3, etc. if needed)
        base_slug = tmpl.slug
        slug = base_slug
        counter = 1
        while await self.role_repo.get_by_slug(slug, tenant_id):
            counter += 1
            slug = f"{base_slug}-{counter}"

        role = await self.role_repo.create(
            name=tmpl.name if counter == 1 else f"{tmpl.name} ({counter})",
            slug=slug,
            description=tmpl.description,
            is_system=False,
            tenant_id=tenant_id,
        )

        # Resolve permission ids from slugs
        all_perms = await self.role_repo.list_permissions()
        perm_map = {p.slug: p.id for p in all_perms}
        perm_ids = [perm_map[s] for s in tmpl.permissions if s in perm_map]
        if perm_ids:
            await self.role_repo.set_role_permissions(role.id, perm_ids)

        return role
