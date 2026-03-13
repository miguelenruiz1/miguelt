"""Factory that returns the active IBlockchainProvider based on settings."""
from __future__ import annotations

from app.clients.blockchain_provider import IBlockchainProvider


def get_blockchain_provider() -> IBlockchainProvider:
    """
    Returns HeliusProvider if HELIUS_API_KEY is configured and SOLANA_SIMULATION is False.
    Falls back to SimulationProvider otherwise.
    """
    from app.core.settings import get_settings
    from app.clients.simulation_provider import SimulationProvider

    settings = get_settings()

    if settings.SOLANA_SIMULATION or not settings.HELIUS_API_KEY:
        return SimulationProvider()

    from app.clients.helius_provider import HeliusProvider
    import httpx

    http = httpx.AsyncClient(timeout=30.0)
    return HeliusProvider(
        api_key=settings.HELIUS_API_KEY,
        rpc_url=settings.HELIUS_RPC_URL,
        http=http,
    )
