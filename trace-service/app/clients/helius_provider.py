"""Helius blockchain provider — uses Helius RPC + DAS API."""
from __future__ import annotations

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
    """

    def __init__(self, api_key: str, rpc_url: str, http: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._rpc_url = rpc_url.rstrip("/")
        self._http = http

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

    async def create_tree(self, config: TreeConfig) -> TreeResult:
        """
        Delegates tree creation to SolanaClient which uses Bubblegum.
        Helius acts as the RPC endpoint for submitting the transaction.
        Returns a simulated result — real tree creation requires a funded keypair.
        """
        # In production, this would call SolanaClient.create_merkle_tree()
        # with Helius as the RPC endpoint. For now, we surface this clearly.
        raise NotImplementedError(
            "Tree creation via HeliusProvider requires a funded fee payer. "
            "Use TenantService.provision_merkle_tree() which handles this."
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
