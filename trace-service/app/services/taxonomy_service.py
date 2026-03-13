"""Business logic for taxonomy (custodian types + organizations)."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.models import Asset, CustodianType, Organization, RegistryWallet
from app.repositories.taxonomy_repo import CustodianTypeRepository, OrganizationRepository

log = get_logger(__name__)


_DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class TaxonomyService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None) -> None:
        self._type_repo = CustodianTypeRepository(session)
        self._org_repo = OrganizationRepository(session)
        self._tenant_id = tenant_id or _DEFAULT_TENANT_ID

    # ── CustodianType ─────────────────────────────────────────────────────────

    async def list_types(self) -> list[CustodianType]:
        return await self._type_repo.list(tenant_id=self._tenant_id)

    async def get_type(self, type_id: uuid.UUID) -> CustodianType:
        ct = await self._type_repo.get(type_id)
        if ct is None or ct.tenant_id != self._tenant_id:
            raise NotFoundError(f"Custodian type '{type_id}' not found")
        return ct

    async def create_type(
        self,
        name: str,
        slug: str,
        color: str,
        icon: str,
        description: str | None,
        sort_order: int,
    ) -> CustodianType:
        existing = await self._type_repo.get_by_slug(slug, tenant_id=self._tenant_id)
        if existing:
            raise ConflictError(f"Custodian type with slug '{slug}' already exists")
        ct = await self._type_repo.create(name, slug, color, icon, description, sort_order, tenant_id=self._tenant_id)
        log.info("custodian_type_created", slug=slug)
        return ct

    async def update_type(self, type_id: uuid.UUID, **values) -> CustodianType:
        await self.get_type(type_id)  # tenant isolation check
        ct = await self._type_repo.update(type_id, **values)
        if ct is None:
            raise NotFoundError(f"Custodian type '{type_id}' not found")
        return ct

    async def delete_type(self, type_id: uuid.UUID) -> None:
        await self.get_type(type_id)  # tenant isolation check
        count = await self._type_repo.count_orgs(type_id)
        if count > 0:
            raise ValidationError(
                f"Cannot delete custodian type with {count} organization(s) attached"
            )
        deleted = await self._type_repo.delete(type_id)
        if not deleted:
            raise NotFoundError(f"Custodian type '{type_id}' not found")

    # ── Organization ──────────────────────────────────────────────────────────

    async def list_orgs(
        self,
        custodian_type_id: uuid.UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Organization], int]:
        return await self._org_repo.list(
            custodian_type_id=custodian_type_id,
            status=status,
            tenant_id=self._tenant_id,
            offset=offset,
            limit=limit,
        )

    async def get_org(self, org_id: uuid.UUID) -> Organization:
        org = await self._org_repo.get(org_id)
        if org is None or org.tenant_id != self._tenant_id:
            raise NotFoundError(f"Organization '{org_id}' not found")
        return org

    async def create_org(
        self,
        name: str,
        custodian_type_id: uuid.UUID,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> Organization:
        ct = await self._type_repo.get(custodian_type_id)
        if ct is None or ct.tenant_id != self._tenant_id:
            raise NotFoundError(f"Custodian type '{custodian_type_id}' not found")
        org = await self._org_repo.create(name, custodian_type_id, description, tags, tenant_id=self._tenant_id)
        log.info("organization_created", name=name, custodian_type_id=str(custodian_type_id))
        return org

    async def update_org(self, org_id: uuid.UUID, **values) -> Organization:
        await self.get_org(org_id)  # tenant isolation check
        org = await self._org_repo.update(org_id, **values)
        if org is None:
            raise NotFoundError(f"Organization '{org_id}' not found")
        return org

    async def delete_org(self, org_id: uuid.UUID) -> None:
        await self.get_org(org_id)  # tenant isolation check
        count = await self._org_repo.count_wallets(org_id)
        if count > 0:
            raise ValidationError(
                f"Cannot delete organization with {count} wallet(s) linked"
            )
        deleted = await self._org_repo.delete(org_id)
        if not deleted:
            raise NotFoundError(f"Organization '{org_id}' not found")

    async def get_org_wallets(
        self, org_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[RegistryWallet], int]:
        await self.get_org(org_id)
        return await self._org_repo.list_wallets(org_id, offset, limit)

    async def get_org_assets(
        self, org_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[Asset], int]:
        await self.get_org(org_id)
        return await self._org_repo.list_assets(org_id, offset, limit)

    async def wallet_count_for_org(self, org_id: uuid.UUID) -> int:
        return await self._org_repo.count_wallets(org_id)
