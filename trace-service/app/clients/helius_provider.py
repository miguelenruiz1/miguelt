"""Helius blockchain provider — uses Helius RPC + DAS API."""
from __future__ import annotations

import base64
import hashlib
import struct
import uuid
from typing import Any

import httpx

from app.clients.blockchain_provider import (
    IBlockchainProvider,
    MintResult,
    TreeConfig,
    TreeResult,
    VerifyResult,
)
from app.core.logging import get_logger

log = get_logger(__name__)

# ─── Solana program IDs ──────────────────────────────────────────────────────
BUBBLEGUM_PROGRAM = "BGUMAp9Gq7iTEuizy4pqaxsTyUCBK68MDfK752saRPUY"
SPL_COMPRESSION_PROGRAM = "cmtDvXumGCrqC1Age74AVPhSRVXJMd8PJS91L8KbNCK"
SPL_NOOP_PROGRAM = "noopb9bkMVfRPU8AsbpTUg8AQkHtKwMYZiFUjNRtMmV"
SYSTEM_PROGRAM = "11111111111111111111111111111111"


class HeliusError(Exception):
    def __init__(self, error_body: dict) -> None:
        code = error_body.get("code", -1)
        message = error_body.get("message", "Unknown Helius error")
        super().__init__(f"Helius RPC error {code}: {message}")
        self.code = code
        self.message = message


class HeliusProvider(IBlockchainProvider):
    """
    Production blockchain provider using Helius API.

    Mint endpoint: mintCompressedNft (JSON-RPC method on Helius RPC endpoint)
    Verify endpoint: getAsset (DAS API, also on the RPC endpoint)
    Tree creation: Bubblegum createTree via standard Solana tx (Helius as RPC)
    """

    def __init__(
        self,
        api_key: str,
        rpc_url: str,
        http: httpx.AsyncClient,
        keypair_raw: str = "",
    ) -> None:
        self._api_key = api_key
        self._rpc_url = rpc_url.rstrip("/")
        self._http = http
        self._keypair_raw = keypair_raw
        self._keypair = None  # solders.Keypair, loaded lazily

    # ─── RPC helpers ──────────────────────────────────────────────────────────

    async def _rpc(self, method: str, params: list | dict) -> Any:
        """JSON-RPC 2.0 call to Helius RPC endpoint."""
        url = f"{self._rpc_url}/?api-key={self._api_key}"
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }
        resp = await self._http.post(url, json=payload, timeout=30.0)
        resp.raise_for_status()
        body = resp.json()
        if "error" in body:
            raise HeliusError(body["error"])
        return body.get("result")

    def _load_keypair(self):
        """Load solders Keypair from base58 string or file path."""
        if self._keypair is not None:
            return self._keypair
        if not self._keypair_raw:
            return None
        try:
            from solders.keypair import Keypair  # type: ignore

            raw = self._keypair_raw.strip()
            if raw.startswith("[") or raw.startswith("/") or "\\" in raw:
                import json as _json
                import pathlib

                p = pathlib.Path(raw)
                if p.exists():
                    data = _json.loads(p.read_text())
                    self._keypair = Keypair.from_bytes(bytes(data))
                else:
                    self._keypair = Keypair.from_bytes(bytes(_json.loads(raw)))
            else:
                from app.clients.solana_client import _b58decode

                self._keypair = Keypair.from_bytes(_b58decode(raw))
            return self._keypair
        except Exception as exc:
            log.warning("helius_keypair_load_failed", exc=str(exc))
            return None

    # ─── IBlockchainProvider implementation ───────────────────────────────────

    async def create_tree(self, config: TreeConfig) -> TreeResult:
        """
        Create a Concurrent Merkle Tree on Solana via Bubblegum program.
        Uses Helius as RPC endpoint. Requires a funded keypair (fee payer).
        """
        keypair = self._load_keypair()
        if keypair is None:
            raise RuntimeError(
                "SOLANA_KEYPAIR required for tree creation. "
                "Set it in .env or use SOLANA_SIMULATION=true."
            )

        try:
            from solders.keypair import Keypair  # type: ignore
            from solders.pubkey import Pubkey  # type: ignore
            from solders.instruction import Instruction, AccountMeta  # type: ignore
            from solders.message import Message  # type: ignore
            from solders.transaction import Transaction  # type: ignore
            from solders.hash import Hash  # type: ignore
            from solders.system_program import (  # type: ignore
                create_account,
                CreateAccountParams,
            )
        except ImportError as exc:
            raise RuntimeError(
                f"solders library required for tree creation: {exc}. "
                "Install it with: pip install solders"
            )

        bubblegum = Pubkey.from_string(BUBBLEGUM_PROGRAM)
        compression = Pubkey.from_string(SPL_COMPRESSION_PROGRAM)
        noop = Pubkey.from_string(SPL_NOOP_PROGRAM)
        system = Pubkey.from_string(SYSTEM_PROGRAM)

        # Generate new keypair for the tree account
        tree_kp = Keypair()

        # Calculate account size for concurrent Merkle tree
        account_size = _merkle_tree_account_size(
            config.max_depth, config.max_buffer_size, config.canopy_depth
        )

        # Get rent-exempt minimum from Solana
        rent_lamports = await self._rpc(
            "getMinimumBalanceForRentExemption", [account_size]
        )

        log.info(
            "creating_merkle_tree",
            depth=config.max_depth,
            buffer=config.max_buffer_size,
            account_bytes=account_size,
            rent_sol=rent_lamports / 1_000_000_000,
        )

        # 1) SystemProgram.createAccount — allocate tree account
        create_ix = create_account(
            CreateAccountParams(
                from_pubkey=keypair.pubkey(),
                to_pubkey=tree_kp.pubkey(),
                lamports=rent_lamports,
                space=account_size,
                owner=compression,
            )
        )

        # 2) Bubblegum.createTree — initialize the tree
        tree_authority, _bump = Pubkey.find_program_address(
            [bytes(tree_kp.pubkey())], bubblegum
        )

        # Anchor discriminator: sha256("global:create_tree")[:8]
        discriminator = hashlib.sha256(b"global:create_tree").digest()[:8]
        # Instruction data: discriminator + max_depth(u32) + max_buffer_size(u32) + public(bool)
        ix_data = discriminator + struct.pack(
            "<IIB", config.max_depth, config.max_buffer_size, 0
        )

        create_tree_ix = Instruction(
            program_id=bubblegum,
            data=ix_data,
            accounts=[
                AccountMeta(tree_authority, is_signer=False, is_writable=True),
                AccountMeta(tree_kp.pubkey(), is_signer=False, is_writable=True),
                AccountMeta(keypair.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(keypair.pubkey(), is_signer=True, is_writable=False),
                AccountMeta(noop, is_signer=False, is_writable=False),
                AccountMeta(compression, is_signer=False, is_writable=False),
                AccountMeta(system, is_signer=False, is_writable=False),
            ],
        )

        # Get recent blockhash
        bh_result = await self._rpc(
            "getLatestBlockhash", [{"commitment": "confirmed"}]
        )
        blockhash = Hash.from_string(bh_result["value"]["blockhash"])

        # Build, sign, and send transaction
        msg = Message.new_with_blockhash(
            [create_ix, create_tree_ix], keypair.pubkey(), blockhash
        )
        tx = Transaction([keypair, tree_kp], msg, blockhash)
        tx_b64 = base64.b64encode(bytes(tx)).decode()

        sig = await self._rpc(
            "sendTransaction",
            [
                tx_b64,
                {
                    "encoding": "base64",
                    "skipPreflight": False,
                    "preflightCommitment": "confirmed",
                },
            ],
        )

        log.info(
            "merkle_tree_created",
            tree=str(tree_kp.pubkey()),
            authority=str(tree_authority),
            tx=str(sig),
        )

        return TreeResult(
            tree_address=str(tree_kp.pubkey()),
            tree_authority=str(tree_authority),
            tx_sig=str(sig),
            is_simulated=False,
        )

    async def mint_cnft(
        self,
        tree_address: str,
        owner_pubkey: str,
        metadata: dict[str, Any],
    ) -> MintResult:
        """
        Mint a cNFT using Helius mintCompressedNft JSON-RPC method.
        Helius manages the fee payer and tree interaction.
        If tree_address is empty, Helius uses a shared tree (free).
        """
        params: dict[str, Any] = {
            "name": metadata.get("name", metadata.get("product_type", "Trace Asset")),
            "symbol": "TRC",
            "owner": owner_pubkey,
            "description": metadata.get("description", ""),
            "attributes": _build_attributes(metadata),
            "imageUrl": metadata.get("image_url", ""),
            "externalUrl": metadata.get("external_url", ""),
            "sellerFeeBasisPoints": 0,
        }
        if tree_address:
            params["treeAddress"] = tree_address

        result = await self._rpc("mintCompressedNft", [params])

        log.info(
            "helius_mint_success",
            asset_id=result.get("assetId"),
            tx=result.get("signature"),
        )

        return MintResult(
            asset_id=result["assetId"],
            tx_signature=result["signature"],
            tree_address=result.get("treeAddress", tree_address),
            leaf_index=result.get("leafIndex"),
            is_simulated=False,
        )

    async def verify_asset(self, asset_id: str) -> VerifyResult:
        """Use DAS API getAsset to verify on-chain state of a cNFT."""
        result = await self._rpc("getAsset", [asset_id])
        compression = result.get("compression", {})
        ownership = result.get("ownership", {})
        return VerifyResult(
            asset_id=asset_id,
            owner=ownership.get("owner", ""),
            tree_address=compression.get("tree", ""),
            leaf_index=compression.get("leaf_id"),
            confirmed=compression.get("compressed", False),
            raw=result,
        )

    async def health_check(self) -> bool:
        try:
            await self._rpc("getHealth", [])
            return True
        except Exception:
            return False


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _merkle_tree_account_size(
    max_depth: int, max_buffer_size: int, canopy_depth: int = 0
) -> int:
    """
    Calculate account size for a Concurrent Merkle Tree.
    Based on SPL Account Compression getConcurrentMerkleTreeAccountSize().
    """
    # Header: version(2) + padding(6) + max_buffer_size(4) + max_depth(4) +
    #         authority(32) + creation_slot(8) + padding(4) = 60
    header_size = 2 + 6 + 4 + 4 + 32 + 8 + 4
    # Changelog: each entry = index(4) + root(32) + path_nodes(max_depth * 32)
    changelog_size = max_buffer_size * (4 + 32 + max_depth * 32)
    # Rightmost proof: path(max_depth * 32) + leaf(32)
    rightmost_path_size = max_depth * 32 + 32
    # Canopy (optional): stores upper tree nodes for cheaper proofs
    canopy_size = ((1 << (canopy_depth + 1)) - 2) * 32 if canopy_depth > 0 else 0
    # 8-byte Anchor discriminator
    return 8 + header_size + changelog_size + rightmost_path_size + canopy_size


def _build_attributes(metadata: dict[str, Any]) -> list[dict[str, str]]:
    """Convert metadata dict to Metaplex-style attribute list."""
    attrs = []
    field_map = {
        "product_type": "Tipo de Producto",
        "weight": "Peso",
        "weight_unit": "Unidad de Peso",
        "quality_grade": "Calidad",
        "origin": "Origen",
        "metadata_hash": "Hash de Integridad",
    }
    for key, label in field_map.items():
        if key in metadata:
            attrs.append({"trait_type": label, "value": str(metadata[key])})
    return attrs
