"""Business logic for wallet registry."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.db.models import Organization, RegistryWallet
from app.domain.types import WalletStatus
from app.repositories.registry_repo import RegistryRepository

log = get_logger(__name__)


_DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class RegistryService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None) -> None:
        self._db = session
        self._repo = RegistryRepository(session)
        self._tenant_id = tenant_id or _DEFAULT_TENANT_ID

    async def _validate_organization_tenant(self, organization_id: uuid.UUID) -> None:
        """Ensure organization belongs to this tenant."""
        from sqlalchemy import select
        result = await self._db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = result.scalar_one_or_none()
        if org is None or org.tenant_id != self._tenant_id:
            raise NotFoundError(f"Organization '{organization_id}' not found")

    async def register_wallet(
        self,
        wallet_pubkey: str,
        tags: list[str],
        status: WalletStatus = WalletStatus.ACTIVE,
        encrypted_private_key: str | None = None,
        name: str | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> RegistryWallet:
        if organization_id is not None:
            await self._validate_organization_tenant(organization_id)

        existing = await self._repo.get_by_pubkey(wallet_pubkey)
        if existing:
            raise ConflictError(
                f"Wallet '{wallet_pubkey}' is already registered",
                wallet_pubkey=wallet_pubkey,
            )
        wallet = await self._repo.create(
            wallet_pubkey,
            tags,
            status,
            encrypted_private_key=encrypted_private_key,
            name=name,
            organization_id=organization_id,
            tenant_id=self._tenant_id,
        )
        log.info("wallet_registered", wallet_id=str(wallet.id), pubkey=wallet_pubkey)
        return wallet

    async def generate_wallet(
        self,
        tags: list[str],
        status: WalletStatus = WalletStatus.ACTIVE,
        name: str | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> tuple[RegistryWallet, dict]:
        """Generate a wallet and attempt a devnet airdrop.

        Returns a tuple `(wallet, airdrop_info)` where `airdrop_info` is
        `{"status": "success"|"failed"|"skipped", "error": str|None}`. Returning
        a tuple (rather than stashing on the ORM instance) is robust against
        future changes to `expire_on_commit`.
        """
        if organization_id is not None:
            await self._validate_organization_tenant(organization_id)

        from app.clients.solana_client import get_solana_client
        from app.core.crypto import encrypt_secret
        client = get_solana_client()
        pubkey, secret = client.generate_wallet()
        # Encrypt the wallet secret key at rest using Fernet (FERNET_KEY in prod
        # is required by settings validator; dev derives from JWT_SECRET).
        encrypted_private_key = encrypt_secret(secret)

        wallet = await self._repo.create(
            wallet_pubkey=pubkey,
            tags=tags,
            status=status,
            encrypted_private_key=encrypted_private_key,
            name=name,
            organization_id=organization_id,
            tenant_id=self._tenant_id,
        )
        log.info("wallet_generated", wallet_id=str(wallet.id), pubkey=pubkey)

        airdrop_status = "skipped"
        airdrop_error: str | None = None
        try:
            airdropped = await client.try_airdrop(pubkey)
            if airdropped:
                airdrop_status = "success"
                log.info("wallet_airdrop_success", pubkey=pubkey)
            else:
                airdrop_status = "failed"
        except Exception as exc:
            airdrop_status = "failed"
            airdrop_error = str(exc)[:200]
            log.warning("wallet_airdrop_failed", pubkey=pubkey, exc=airdrop_error)

        return wallet, {"status": airdrop_status, "error": airdrop_error}

    async def get_wallet(self, wallet_id: uuid.UUID) -> RegistryWallet:
        wallet = await self._repo.get_by_id(wallet_id)
        if wallet is None or wallet.tenant_id != self._tenant_id:
            raise NotFoundError(f"Wallet '{wallet_id}' not found")
        return wallet

    async def list_wallets(
        self,
        tag: str | None = None,
        status: str | None = None,
        organization_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[RegistryWallet], int]:
        return await self._repo.list(
            tag=tag,
            status=status,
            organization_id=organization_id,
            tenant_id=self._tenant_id,
            offset=offset,
            limit=limit,
        )

    async def update_wallet(
        self,
        wallet_id: uuid.UUID,
        tags: list[str] | None = None,
        status: WalletStatus | None = None,
        name: str | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> RegistryWallet:
        # Verify wallet belongs to this tenant
        existing = await self._repo.get_by_id(wallet_id)
        if existing is None or existing.tenant_id != self._tenant_id:
            raise NotFoundError(f"Wallet '{wallet_id}' not found")
        if organization_id is not None:
            await self._validate_organization_tenant(organization_id)
        updated = await self._repo.update(
            wallet_id,
            tags=tags,
            status=status,
            name=name,
            organization_id=organization_id,
        )
        if updated is None:
            raise NotFoundError(f"Wallet '{wallet_id}' not found")
        log.info("wallet_updated", wallet_id=str(wallet_id))
        return updated

    async def assert_wallet_active(self, pubkey: str) -> None:
        """Raise WalletNotAllowlistedError if pubkey is not allowlisted active."""
        from app.core.errors import WalletNotAllowlistedError
        is_active = await self._repo.is_active(pubkey)
        if not is_active:
            raise WalletNotAllowlistedError(
                f"Wallet '{pubkey}' is not in the active allowlist",
                wallet_pubkey=pubkey,
            )
