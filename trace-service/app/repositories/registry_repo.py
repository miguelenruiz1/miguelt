"""Repository: registry_wallets table."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RegistryWallet
from app.domain.types import WalletStatus


class RegistryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def create(
        self,
        wallet_pubkey: str,
        tags: list[str],
        status: WalletStatus = WalletStatus.ACTIVE,
        encrypted_private_key: str | None = None,
        name: str | None = None,
        organization_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> RegistryWallet:
        now = datetime.now(tz=timezone.utc)
        wallet = RegistryWallet(
            id=uuid.uuid4(),
            wallet_pubkey=wallet_pubkey,
            encrypted_private_key=encrypted_private_key,
            name=name,
            organization_id=organization_id,
            tenant_id=tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000001"),
            tags=tags,
            status=status,
            created_at=now,
            updated_at=now,
        )
        self._db.add(wallet)
        await self._db.flush()
        return wallet

    async def get_by_id(self, wallet_id: uuid.UUID) -> RegistryWallet | None:
        result = await self._db.execute(
            select(RegistryWallet).where(RegistryWallet.id == wallet_id)
        )
        return result.scalar_one_or_none()

    async def get_by_pubkey(self, pubkey: str) -> RegistryWallet | None:
        result = await self._db.execute(
            select(RegistryWallet).where(RegistryWallet.wallet_pubkey == pubkey)
        )
        return result.scalar_one_or_none()

    async def is_active(self, pubkey: str) -> bool:
        result = await self._db.execute(
            select(RegistryWallet.id).where(
                RegistryWallet.wallet_pubkey == pubkey,
                RegistryWallet.status == WalletStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none() is not None

    async def find_by_tag(
        self, tenant_id: uuid.UUID, tag: str
    ) -> RegistryWallet | None:
        """Find first active wallet with a specific tag for a tenant."""
        result = await self._db.execute(
            select(RegistryWallet).where(
                RegistryWallet.tenant_id == tenant_id,
                RegistryWallet.status == WalletStatus.ACTIVE,
                RegistryWallet.tags.contains([tag]),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        tag: str | None = None,
        status: str | None = None,
        organization_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[RegistryWallet], int]:
        q = select(RegistryWallet)
        count_q = select(func.count(RegistryWallet.id))

        if tenant_id is not None:
            q = q.where(RegistryWallet.tenant_id == tenant_id)
            count_q = count_q.where(RegistryWallet.tenant_id == tenant_id)
        if tag:
            q = q.where(RegistryWallet.tags.contains([tag]))
            count_q = count_q.where(RegistryWallet.tags.contains([tag]))
        if status:
            q = q.where(RegistryWallet.status == status)
            count_q = count_q.where(RegistryWallet.status == status)
        if organization_id is not None:
            q = q.where(RegistryWallet.organization_id == organization_id)
            count_q = count_q.where(RegistryWallet.organization_id == organization_id)

        total = (await self._db.execute(count_q)).scalar_one()
        rows = (await self._db.execute(q.offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def update(
        self,
        wallet_id: uuid.UUID,
        tags: list[str] | None = None,
        status: WalletStatus | None = None,
        name: str | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> RegistryWallet | None:
        values: dict = {"updated_at": datetime.now(tz=timezone.utc)}
        if tags is not None:
            values["tags"] = tags
        if status is not None:
            values["status"] = status
        if name is not None:
            values["name"] = name
        if organization_id is not None:
            values["organization_id"] = organization_id

        await self._db.execute(
            update(RegistryWallet)
            .where(RegistryWallet.id == wallet_id)
            .values(**values)
        )
        await self._db.flush()
        return await self.get_by_id(wallet_id)
