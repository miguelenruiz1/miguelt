"""Abstract blockchain provider interface (Adapter/Strategy pattern)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TreeConfig:
    max_depth: int = 14
    max_buffer_size: int = 64
    canopy_depth: int = 0


@dataclass
class TreeResult:
    tree_address: str
    tree_authority: str
    tx_sig: str | None
    is_simulated: bool


@dataclass
class MintResult:
    asset_id: str           # ID del cNFT en Helius/DAS
    tx_signature: str
    tree_address: str
    leaf_index: int | None
    is_simulated: bool


@dataclass
class VerifyResult:
    asset_id: str
    owner: str
    tree_address: str
    leaf_index: int | None
    confirmed: bool
    raw: dict = field(default_factory=dict)


class IBlockchainProvider(ABC):
    """
    Interface for blockchain providers.
    CustodyService never references this directly — BlockchainService does.
    """

    @abstractmethod
    async def create_tree(self, config: TreeConfig) -> TreeResult:
        """Create a Concurrent Merkle Tree on Solana."""
        ...

    @abstractmethod
    async def mint_cnft(
        self,
        tree_address: str,
        owner_pubkey: str,
        metadata: dict[str, Any],
    ) -> MintResult:
        """Mint a compressed NFT and return its on-chain identifiers."""
        ...

    @abstractmethod
    async def verify_asset(self, asset_id: str) -> VerifyResult:
        """Verify on-chain state of a cNFT via DAS API."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
        ...
