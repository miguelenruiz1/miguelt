"""
BlockchainService — orchestrates cNFT minting and verification.

Responsibilities:
- Build normalized metadata for a logistics asset
- Compute SHA256 hash of metadata (integrity proof)
- Call the active IBlockchainProvider to mint
- Persist blockchain_* fields on Asset
- On failure: mark FAILED, enqueue ARQ retry (fire-and-forget)
- NEVER raises exceptions — failures are absorbed and logged
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.blockchain_provider import IBlockchainProvider, VerifyResult
from app.core.logging import get_logger
from app.repositories.custody_repo import AssetRepository
from app.repositories.tenant_repo import TenantRepository

log = get_logger(__name__)


class BlockchainService:
    def __init__(self, session: AsyncSession, provider: IBlockchainProvider) -> None:
        self._db = session
        self._provider = provider
        self._asset_repo = AssetRepository(session)
        self._tenant_repo = TenantRepository(session)

    def _build_metadata(self, product_type: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Return normalized metadata dict for a logistics cNFT."""
        return {
            "name": metadata.get("name", product_type),
            "product_type": product_type,
            "symbol": "TRC",
            **{k: v for k, v in metadata.items() if k not in ("name",)},
        }

    def _compute_metadata_hash(self, metadata: dict[str, Any]) -> str:
        """SHA256 of attributes sorted alphabetically (deterministic)."""
        sorted_str = json.dumps(metadata, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(sorted_str.encode("utf-8")).hexdigest()

    async def mint_asset_onchain(
        self,
        asset_id: uuid.UUID,
        tenant_id: uuid.UUID,
        product_type: str,
        metadata: dict[str, Any],
        owner_pubkey: str,
    ) -> None:
        """
        Attempt to mint a cNFT for the given asset.
        NEVER raises — failures are absorbed and stored as FAILED status.
        """
        try:
            tree = await self._tenant_repo.get_merkle_tree(tenant_id)
            if tree is None:
                log.warning(
                    "no_merkle_tree_for_tenant",
                    tenant_id=str(tenant_id),
                    asset_id=str(asset_id),
                )
                await self._update_status(asset_id, "FAILED", error="No Merkle tree provisioned for tenant")
                return

            normalized_meta = self._build_metadata(product_type, metadata)
            normalized_meta["metadata_hash"] = self._compute_metadata_hash(normalized_meta)

            result = await self._provider.mint_cnft(
                tree_address=tree.tree_address,
                owner_pubkey=owner_pubkey,
                metadata=normalized_meta,
            )

            await self._tenant_repo.increment_leaf_count(tenant_id)

            new_status = "SIMULATED" if result.is_simulated else "CONFIRMED"
            await self._asset_repo.update_blockchain_fields(
                asset_id=asset_id,
                blockchain_asset_id=result.asset_id,
                blockchain_tree_address=result.tree_address,
                blockchain_tx_signature=result.tx_signature,
                blockchain_status=new_status,
                is_compressed=True,
            )

            log.info(
                "cnft_minted",
                asset_id=str(asset_id),
                blockchain_asset_id=result.asset_id,
                tree=result.tree_address,
                tx=result.tx_signature,
                simulated=result.is_simulated,
            )

        except Exception as exc:
            log.error("cnft_mint_failed", asset_id=str(asset_id), exc=str(exc))
            await self._update_status(asset_id, "FAILED", error=str(exc))
            await _enqueue_blockchain_retry(asset_id)

    async def verify_asset_onchain(self, asset_id_db: uuid.UUID) -> VerifyResult | None:
        """Verify on-chain state of an asset using DAS API."""
        asset = await self._asset_repo.get_by_id(asset_id_db)
        if not asset or not asset.blockchain_asset_id:
            return None
        try:
            result = await self._provider.verify_asset(asset.blockchain_asset_id)
            if result.confirmed:
                await self._update_status(asset_id_db, "CONFIRMED")
            return result
        except Exception as exc:
            log.warning("cnft_verify_failed", asset_id=str(asset_id_db), exc=str(exc))
            return None

    async def _update_status(
        self, asset_id: uuid.UUID, status: str, error: str | None = None
    ) -> None:
        await self._asset_repo.update_blockchain_fields(
            asset_id=asset_id,
            blockchain_status=status,
            blockchain_error=error,
        )


async def _enqueue_blockchain_retry(asset_id: uuid.UUID) -> None:
    """Best-effort enqueue of retry job via ARQ. Swallows errors."""
    try:
        from app.services.anchor_service import _get_arq_pool
        pool = await _get_arq_pool()
        if pool:
            await pool.enqueue_job("retry_blockchain_mint", str(asset_id))
    except Exception as exc:
        log.warning("enqueue_blockchain_retry_failed", asset_id=str(asset_id), exc=str(exc))
