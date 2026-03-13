"""Business logic for tenant management and Merkle tree provisioning."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.blockchain_provider import TreeConfig
from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.db.models import Tenant, TenantMerkleTree
from app.repositories.tenant_repo import TenantRepository

log = get_logger(__name__)


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = TenantRepository(session)

    async def create_tenant(self, name: str, slug: str) -> Tenant:
        existing = await self._repo.get_by_slug(slug)
        if existing:
            raise ConflictError(f"Tenant with slug '{slug}' already exists")
        tenant = await self._repo.create(name=name, slug=slug)
        log.info("tenant_created", tenant_id=str(tenant.id), slug=slug)
        return tenant

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self._repo.get_by_id(tenant_id)
        if tenant is None:
            raise NotFoundError(f"Tenant '{tenant_id}' not found")
        return tenant

    async def list_tenants(self) -> list[Tenant]:
        return await self._repo.list()

    async def provision_merkle_tree(
        self,
        tenant_id: uuid.UUID,
        config: TreeConfig | None = None,
    ) -> TenantMerkleTree:
        """
        Create a Merkle tree for the tenant.
        Uses the active IBlockchainProvider (simulation or Helius).
        """
        tenant = await self.get_tenant(tenant_id)

        # Check if already provisioned
        existing = await self._repo.get_merkle_tree(tenant_id)
        if existing:
            raise ConflictError(f"Tenant '{tenant_id}' already has a Merkle tree provisioned")

        cfg = config or TreeConfig()

        from app.clients.provider_factory import get_blockchain_provider
        provider = get_blockchain_provider()
        tree_result = await provider.create_tree(cfg)

        tree = await self._repo.create_merkle_tree(
            tenant_id=tenant_id,
            tree_address=tree_result.tree_address,
            tree_authority=tree_result.tree_authority,
            max_depth=cfg.max_depth,
            max_buffer_size=cfg.max_buffer_size,
            canopy_depth=cfg.canopy_depth,
            create_tx_sig=tree_result.tx_sig,
            is_simulated=tree_result.is_simulated,
        )

        log.info(
            "merkle_tree_provisioned",
            tenant_id=str(tenant_id),
            tree_address=tree_result.tree_address,
            simulated=tree_result.is_simulated,
        )
        return tree

    async def get_merkle_tree(self, tenant_id: uuid.UUID) -> TenantMerkleTree:
        tree = await self._repo.get_merkle_tree(tenant_id)
        if tree is None:
            raise NotFoundError(f"No Merkle tree found for tenant '{tenant_id}'")
        return tree
