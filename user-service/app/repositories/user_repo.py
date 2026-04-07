"""User repository."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Permission, Role, RolePermission, User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> User:
        user = User(**kwargs)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, tenant_id: str | None = None) -> User | None:
        """Lookup by email. Now that email is unique-per-tenant (not global,
        migration 016), callers MUST pass tenant_id to avoid MultipleResultsFound.
        For legacy callers without tenant context, returns the first match
        deterministically (active first, then by creation date).
        """
        q = select(User).where(User.email == email)
        if tenant_id is not None:
            q = q.where(User.tenant_id == tenant_id)
        else:
            # Legacy fallback: prefer active users, oldest first
            q = q.order_by(User.is_active.desc(), User.created_at.asc()).limit(1)
        result = await self.db.execute(q)
        return result.scalars().first()

    async def get_by_username(self, username: str, tenant_id: str | None = None) -> User | None:
        q = select(User).where(User.username == username)
        if tenant_id is not None:
            q = q.where(User.tenant_id == tenant_id)
        else:
            q = q.order_by(User.is_active.desc(), User.created_at.asc()).limit(1)
        result = await self.db.execute(q)
        return result.scalars().first()

    async def get_by_invitation_token(self, token: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.invitation_token == token)
        )
        return result.scalar_one_or_none()

    async def update(self, user: User, **kwargs) -> User:
        for k, v in kwargs.items():
            setattr(user, k, v)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def list(
        self,
        tenant_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[User], int]:
        q = select(User).where(User.tenant_id == tenant_id)
        total_result = await self.db.execute(select(func.count()).select_from(q.subquery()))
        total = total_result.scalar_one()
        result = await self.db.execute(q.offset(offset).limit(limit))
        return list(result.scalars()), total

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        tenant_id: str | None = None,
    ) -> tuple[list[User], int]:
        """List users across all tenants (superuser-only)."""
        q = select(User)
        if tenant_id:
            q = q.where(User.tenant_id == tenant_id)
        if search:
            pattern = f"%{search}%"
            q = q.where(
                User.email.ilike(pattern) | User.full_name.ilike(pattern) | User.username.ilike(pattern)
            )
        total_result = await self.db.execute(select(func.count()).select_from(q.subquery()))
        total = total_result.scalar_one()
        result = await self.db.execute(q.order_by(User.created_at.desc()).offset(offset).limit(limit))
        return list(result.scalars()), total

    async def count_active(self, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).where(User.tenant_id == tenant_id, User.is_active.is_(True))
        )
        return result.scalar_one()

    async def get_user_roles(self, user_id: str) -> list[Role]:
        result = await self.db.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return list(result.scalars())

    async def get_user_permissions(self, user_id: str) -> set[str]:
        result = await self.db.execute(
            select(Permission.slug)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .distinct()
        )
        return set(result.scalars())
