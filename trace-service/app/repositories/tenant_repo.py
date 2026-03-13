"""Repository: tenants + tenant_merkle_trees tables."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Tenant, TenantMerkleTree


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def create(
        self,
        name: str,
        slug: str,
        status: str = "active",
        metadata: dict | None = None,
    ) -> Tenant:
        now = datetime.now(tz=timezone.utc)
        tenant = Tenant(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            status=status,
            metadata_=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self._db.add(tenant)
        await self._db.flush()
        return tenant

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        result = await self._db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self._db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list(self) -> list[Tenant]:
        result = await self._db.execute(select(Tenant).order_by(Tenant.name))
        return list(result.scalars().all())

    # ─── Merkle tree ops ──────────────────────────────────────────────────────

    async def get_merkle_tree(self, tenant_id: uuid.UUID) -> TenantMerkleTree | None:
        result = await self._db.execute(
            select(TenantMerkleTree).where(TenantMerkleTree.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_merkle_tree(
        self,
        tenant_id: uuid.UUID,
        tree_address: str,
        tree_authority: str,
        max_depth: int = 14,
        max_buffer_size: int = 64,
        canopy_depth: int = 0,
        create_tx_sig: str | None = None,
        is_simulated: bool = False,
    ) -> TenantMerkleTree:
        now = datetime.now(tz=timezone.utc)
        tree = TenantMerkleTree(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            tree_address=tree_address,
            tree_authority=tree_authority,
            max_depth=max_depth,
            max_buffer_size=max_buffer_size,
            canopy_depth=canopy_depth,
            leaf_count=0,
            create_tx_sig=create_tx_sig,
            is_simulated=is_simulated,
            created_at=now,
            updated_at=now,
        )
        self._db.add(tree)
        await self._db.flush()
        return tree

    async def increment_leaf_count(self, tenant_id: uuid.UUID) -> int:
        """Atomically increment leaf_count and return new value."""
        result = await self._db.execute(
            select(TenantMerkleTree.leaf_count).where(
                TenantMerkleTree.tenant_id == tenant_id
            )
        )
        current = result.scalar_one_or_none() or 0
        new_count = current + 1
        await self._db.execute(
            update(TenantMerkleTree)
            .where(TenantMerkleTree.tenant_id == tenant_id)
            .values(leaf_count=new_count, updated_at=datetime.now(tz=timezone.utc))
        )
        await self._db.flush()
        return new_count
