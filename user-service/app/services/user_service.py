"""User management service."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.security import hash_password, verify_password
from app.core.errors import ConflictError, ValidationError
from app.db.models import Role, User
from app.repositories.role_repo import RoleRepository
from app.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    async def list(self, tenant_id: str, offset: int = 0, limit: int = 50) -> tuple[list[User], int]:
        return await self.user_repo.list(tenant_id, offset, limit)

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        tenant_id: str | None = None,
    ) -> tuple[list[User], int]:
        """List users across all tenants (superuser-only)."""
        return await self.user_repo.list_all(offset=offset, limit=limit, search=search, tenant_id=tenant_id)

    async def get(self, user_id: str) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def update(self, user_id: str, **kwargs) -> User:
        user = await self.get(user_id)
        return await self.user_repo.update(user, **kwargs)

    async def deactivate(self, user_id: str) -> User:
        user = await self.get(user_id)
        return await self.user_repo.update(user, is_active=False)

    async def change_password(self, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.password_hash):
            raise ValidationError("Current password is incorrect")
        return await self.user_repo.update(user, password_hash=hash_password(new_password))

    async def assign_role(self, user_id: str, role_id: str) -> None:
        user = await self.get(user_id)
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role {role_id} not found")
        await self.role_repo.assign_role_to_user(user.id, role.id)

    async def remove_role(self, user_id: str, role_id: str) -> None:
        user = await self.get(user_id)
        await self.role_repo.remove_role_from_user(user.id, role_id)
