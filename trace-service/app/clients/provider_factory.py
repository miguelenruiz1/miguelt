"""
Factory that returns the active IBlockchainProvider based on settings.

Switch logic (controlled by env vars):
  SOLANA_SIMULATION=true  → SimulationProvider  (default, sin red)
  SOLANA_SIMULATION=false + HELIUS_API_KEY set  → HeliusProvider  (Helius RPC + DAS)
  SOLANA_SIMULATION=false + HELIUS_API_KEY empty → SimulationProvider con warning
"""
from __future__ import annotations

from app.clients.blockchain_provider import IBlockchainProvider
from app.core.logging import get_logger

log = get_logger(__name__)


def get_blockchain_provider() -> IBlockchainProvider:
    """Return the blockchain provider based on current settings."""
    from app.core.settings import get_settings

    settings = get_settings()

    # ── Simulation mode ───────────────────────────────────────────────────
    if settings.SOLANA_SIMULATION:
        from app.clients.simulation_provider import SimulationProvider

        return SimulationProvider()

    # ── Real mode: requires Helius API key ────────────────────────────────
    if not settings.HELIUS_API_KEY:
        log.warning(
            "solana_simulation_off_but_no_helius_key",
            hint="Set HELIUS_API_KEY or use SOLANA_SIMULATION=true",
        )
        from app.clients.simulation_provider import SimulationProvider

        return SimulationProvider()

    from app.clients.helius_provider import HeliusProvider
    import httpx

    http = httpx.AsyncClient(timeout=settings.SOLANA_TIMEOUT)
    return HeliusProvider(
        api_key=settings.HELIUS_API_KEY,
        rpc_url=settings.effective_helius_rpc_url,
        http=http,
        keypair_raw=settings.SOLANA_KEYPAIR,
    )
