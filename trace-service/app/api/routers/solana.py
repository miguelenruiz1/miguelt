"""Solana debug/utility endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from app.clients.solana_client import get_solana_client
from app.core.settings import get_settings
from app.domain.schemas import SolanaAccountResponse, SolanaTxResponse

router = APIRouter(prefix="/solana", tags=["solana"])


@router.get(
    "/status",
    summary="Current blockchain connection mode and config",
)
async def blockchain_status() -> ORJSONResponse:
    """Blockchain mode + Helius health + fee payer balance (real devnet)."""
    settings = get_settings()
    client = get_solana_client()

    helius_healthy = None
    if settings.blockchain_mode == "helius":
        from app.clients.provider_factory import get_blockchain_provider

        provider = get_blockchain_provider()
        helius_healthy = await provider.health_check()

    fee_payer_balance = None
    fee_payer_pubkey = None
    if settings.SOLANA_KEYPAIR:
        kp = client._load_keypair()
        if kp:
            fee_payer_pubkey = str(kp.pubkey())
            try:
                info = await client.get_account_info(fee_payer_pubkey)
                lamports = info.get("lamports")
                if lamports is not None:
                    fee_payer_balance = lamports / 1_000_000_000
            except Exception:
                pass

    return ORJSONResponse(content={
        "mode": settings.blockchain_mode,
        "network": settings.SOLANA_NETWORK,
        "rpc_url": settings.SOLANA_RPC_URL,
        "helius_configured": bool(settings.HELIUS_API_KEY),
        "helius_healthy": helius_healthy,
        "fee_payer": fee_payer_pubkey,
        "fee_payer_balance_sol": fee_payer_balance,
        "commitment": settings.SOLANA_COMMITMENT,
        "circuit_breaker": client._cb.state.value,
    })


@router.get(
    "/account/{pubkey}",
    response_model=SolanaAccountResponse,
    summary="Get Solana account info",
)
async def get_account(pubkey: str) -> ORJSONResponse:
    client = get_solana_client()
    info = await client.get_account_info(pubkey)
    return ORJSONResponse(content=info)


@router.get(
    "/tx/{sig}",
    response_model=SolanaTxResponse,
    summary="Get Solana transaction status",
)
async def get_tx(sig: str) -> ORJSONResponse:
    client = get_solana_client()
    status = await client.get_signature_status(sig)
    return ORJSONResponse(content=status)
