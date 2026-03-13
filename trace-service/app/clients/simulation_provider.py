"""Simulation blockchain provider — no real Solana calls."""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

from app.clients.blockchain_provider import (
    IBlockchainProvider,
    MintResult,
    TreeConfig,
    TreeResult,
    VerifyResult,
)


class SimulationProvider(IBlockchainProvider):
    """
    Deterministic provider for development and testing.
    Never makes network calls. Returns consistent fake values.
    """

    async def create_tree(self, config: TreeConfig) -> TreeResult:
        tree_id = uuid.uuid4().hex
        return TreeResult(
            tree_address="simTree" + tree_id[:36],
            tree_authority="simAuth" + tree_id[:36],
            tx_sig=None,
            is_simulated=True,
        )

    async def mint_cnft(
        self,
        tree_address: str,
        owner_pubkey: str,
        metadata: dict[str, Any],
    ) -> MintResult:
        raw = (tree_address + owner_pubkey + str(sorted(metadata.items()))).encode()
        asset_id = "simAsset" + hashlib.sha256(raw).hexdigest()[:36]
        tx_sig = "simTx" + uuid.uuid4().hex
        return MintResult(
            asset_id=asset_id,
            tx_signature=tx_sig,
            tree_address=tree_address,
            leaf_index=None,
            is_simulated=True,
        )

    async def verify_asset(self, asset_id: str) -> VerifyResult:
        return VerifyResult(
            asset_id=asset_id,
            owner="simOwner",
            tree_address="simTree",
            leaf_index=0,
            confirmed=True,
            raw={},
        )

    async def health_check(self) -> bool:
        return True
