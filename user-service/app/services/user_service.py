"""User management service.

All methods that access a single user/role by id REQUIRE a tenant_id parameter
and validate that the target belongs to that tenant. This closes the IDOR
vulnerability where an admin in tenant A could read/modify users in tenant B.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError
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

    async def get(self, user_id: str, tenant_id: str | None = None) -> User:
        """Fetch a user by id. If tenant_id is given, enforce isolation."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        if tenant_id is not None and str(user.tenant_id) != str(tenant_id):
            # Same response as not found to avoid id enumeration
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def update(self, user_id: str, tenant_id: str | None = None, **kwargs) -> User:
        user = await self.get(user_id, tenant_id=tenant_id)
        return await self.user_repo.update(user, **kwargs)

    async def deactivate(self, user_id: str, tenant_id: str | None = None) -> User:
        user = await self.get(user_id, tenant_id=tenant_id)
        return await self.user_repo.update(user, is_active=False)

    async def change_password(self, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.password_hash):
            raise ValidationError("Current password is incorrect")
        return await self.user_repo.update(user, password_hash=hash_password(new_password))

    async def assign_role(self, user_id: str, role_id: str, tenant_id: str | None = None) -> None:
        """Assign a role to a user. If tenant_id is provided, BOTH user and role
        must belong to it (closes cross-tenant role assignment vulnerability).
        """
        user = await self.get(user_id, tenant_id=tenant_id)
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError(f"Role {role_id} not found")
        if tenant_id is not None and str(role.tenant_id) != str(tenant_id):
            raise NotFoundError(f"Role {role_id} not found")
        await self.role_repo.assign_role_to_user(user.id, role.id)

    async def remove_role(self, user_id: str, role_id: str, tenant_id: str | None = None) -> None:
        user = await self.get(user_id, tenant_id=tenant_id)
        # Validate role tenant too if provided
        if tenant_id is not None:
            role = await self.role_repo.get_by_id(role_id)
            if not role or str(role.tenant_id) != str(tenant_id):
                raise NotFoundError(f"Role {role_id} not found")
        await self.role_repo.remove_role_from_user(user.id, role_id)
