"""Role and permission repository."""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Permission, Role, RolePermission, UserRole


class RoleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> Role:
        role = Role(**kwargs)
        self.db.add(role)
        await self.db.flush()
        await self.db.refresh(role)
        return role

    async def get_by_id(self, role_id: str) -> Role | None:
        result = await self.db.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str, tenant_id: str) -> Role | None:
        result = await self.db.execute(
            select(Role).where(Role.slug == slug, Role.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list(self, tenant_id: str) -> list[Role]:
        result = await self.db.execute(
            select(Role).where(Role.tenant_id == tenant_id).order_by(Role.name)
        )
        return list(result.scalars())

    async def update(self, role: Role, **kwargs) -> Role:
        for k, v in kwargs.items():
            setattr(role, k, v)
        await self.db.flush()
        await self.db.refresh(role)
        return role

    async def delete(self, role: Role) -> None:
        self.db.delete(role)
        await self.db.flush()

    # ── Permissions ─────────────────────────────────────────────────────────

    async def list_permissions(self) -> list[Permission]:
        result = await self.db.execute(
            select(Permission).order_by(Permission.module, Permission.slug)
        )
        return list(result.scalars())

    async def get_permission_by_id(self, perm_id: str) -> Permission | None:
        result = await self.db.execute(select(Permission).where(Permission.id == perm_id))
        return result.scalar_one_or_none()

    async def get_or_create_permission(self, slug: str, module: str, name: str) -> Permission:
        result = await self.db.execute(select(Permission).where(Permission.slug == slug))
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        perm = Permission(slug=slug, module=module, name=name)
        self.db.add(perm)
        await self.db.flush()
        return perm

    async def get_role_permissions(self, role_id: str) -> list[Permission]:
        result = await self.db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
            .order_by(Permission.module, Permission.slug)
        )
        return list(result.scalars())

    async def set_role_permissions(self, role_id: str, perm_ids: list[str]) -> None:
        """Replace all permissions for a role."""
        await self.db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        if perm_ids:
            rows = [{"role_id": role_id, "permission_id": pid} for pid in perm_ids]
            await self.db.execute(pg_insert(RolePermission).values(rows).on_conflict_do_nothing())
        await self.db.flush()

    # ── User-Role assignment ─────────────────────────────────────────────────

    async def assign_role_to_user(self, user_id: str, role_id: str) -> None:
        stmt = pg_insert(UserRole).values(user_id=user_id, role_id=role_id).on_conflict_do_nothing()
        await self.db.execute(stmt)
        await self.db.flush()

    async def remove_role_from_user(self, user_id: str, role_id: str) -> None:
        await self.db.execute(
            delete(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        await self.db.flush()
