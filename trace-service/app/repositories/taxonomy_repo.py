"""Repositories: custodian_types and organizations tables."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Asset, CustodianType, Organization, RegistryWallet


class CustodianTypeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list(self, tenant_id: uuid.UUID | None = None) -> list[CustodianType]:
        q = select(CustodianType).order_by(CustodianType.sort_order, CustodianType.name)
        if tenant_id is not None:
            q = q.where(CustodianType.tenant_id == tenant_id)
        result = await self._db.execute(q)
        return list(result.scalars().all())

    async def get(self, type_id: uuid.UUID) -> CustodianType | None:
        result = await self._db.execute(
            select(CustodianType).where(CustodianType.id == type_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str, tenant_id: uuid.UUID | None = None) -> CustodianType | None:
        q = select(CustodianType).where(CustodianType.slug == slug)
        if tenant_id is not None:
            q = q.where(CustodianType.tenant_id == tenant_id)
        result = await self._db.execute(q)
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        slug: str,
        color: str,
        icon: str,
        description: str | None,
        sort_order: int,
        tenant_id: uuid.UUID | None = None,
    ) -> CustodianType:
        now = datetime.now(tz=timezone.utc)
        ct = CustodianType(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            color=color,
            icon=icon,
            description=description,
            sort_order=sort_order,
            tenant_id=tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000001"),
            created_at=now,
            updated_at=now,
        )
        self._db.add(ct)
        await self._db.flush()
        return ct

    async def update(self, type_id: uuid.UUID, **values) -> CustodianType | None:
        values["updated_at"] = datetime.now(tz=timezone.utc)
        await self._db.execute(
            update(CustodianType).where(CustodianType.id == type_id).values(**values)
        )
        await self._db.flush()
        return await self.get(type_id)

    async def delete(self, type_id: uuid.UUID) -> bool:
        result = await self._db.execute(
            delete(CustodianType).where(CustodianType.id == type_id)
        )
        return result.rowcount > 0

    async def count_orgs(self, type_id: uuid.UUID) -> int:
        result = await self._db.execute(
            select(func.count(Organization.id)).where(
                Organization.custodian_type_id == type_id
            )
        )
        return result.scalar_one()


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list(
        self,
        custodian_type_id: uuid.UUID | None = None,
        status: str | None = None,
        tenant_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Organization], int]:
        q = select(Organization)
        count_q = select(func.count(Organization.id))

        if tenant_id is not None:
            q = q.where(Organization.tenant_id == tenant_id)
            count_q = count_q.where(Organization.tenant_id == tenant_id)
        if custodian_type_id:
            q = q.where(Organization.custodian_type_id == custodian_type_id)
            count_q = count_q.where(Organization.custodian_type_id == custodian_type_id)
        if status:
            q = q.where(Organization.status == status)
            count_q = count_q.where(Organization.status == status)

        total = (await self._db.execute(count_q)).scalar_one()
        rows = (await self._db.execute(q.offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def get(self, org_id: uuid.UUID) -> Organization | None:
        result = await self._db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        custodian_type_id: uuid.UUID,
        description: str | None = None,
        tags: list[str] | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> Organization:
        now = datetime.now(tz=timezone.utc)
        org = Organization(
            id=uuid.uuid4(),
            name=name,
            custodian_type_id=custodian_type_id,
            description=description,
            tags=tags or [],
            status="active",
            metadata_={},
            tenant_id=tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000001"),
            created_at=now,
            updated_at=now,
        )
        self._db.add(org)
        await self._db.flush()
        return org

    async def update(self, org_id: uuid.UUID, **values) -> Organization | None:
        values["updated_at"] = datetime.now(tz=timezone.utc)
        await self._db.execute(
            update(Organization).where(Organization.id == org_id).values(**values)
        )
        await self._db.flush()
        return await self.get(org_id)

    async def delete(self, org_id: uuid.UUID) -> bool:
        result = await self._db.execute(
            delete(Organization).where(Organization.id == org_id)
        )
        return result.rowcount > 0

    async def count_wallets(self, org_id: uuid.UUID) -> int:
        result = await self._db.execute(
            select(func.count(RegistryWallet.id)).where(
                RegistryWallet.organization_id == org_id
            )
        )
        return result.scalar_one()

    async def list_wallets(
        self, org_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[RegistryWallet], int]:
        count = await self.count_wallets(org_id)
        rows = (
            await self._db.execute(
                select(RegistryWallet)
                .where(RegistryWallet.organization_id == org_id)
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return list(rows), count

    async def list_assets(
        self, org_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[Asset], int]:
        """Assets whose current custodian wallet belongs to this org."""
        pubkey_subq = (
            select(RegistryWallet.wallet_pubkey)
            .where(RegistryWallet.organization_id == org_id)
            .scalar_subquery()
        )
        q = select(Asset).where(Asset.current_custodian_wallet.in_(pubkey_subq))
        count_q = select(func.count(Asset.id)).where(
            Asset.current_custodian_wallet.in_(pubkey_subq)
        )
        total = (await self._db.execute(count_q)).scalar_one()
        rows = (await self._db.execute(q.offset(offset).limit(limit))).scalars().all()
        return list(rows), total
