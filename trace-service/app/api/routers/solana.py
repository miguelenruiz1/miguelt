"""Solana debug/utility endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from app.clients.solana_client import get_solana_client
from app.domain.schemas import SolanaAccountResponse, SolanaTxResponse

router = APIRouter(prefix="/solana", tags=["solana"])


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
