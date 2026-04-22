"""
Factory del IBlockchainProvider activo.

CLAUDE.md regla #0.bis: el único provider soportado es HeliusProvider contra
Solana real (devnet por defecto). La simulación fue eliminada del código —
no hay fallback silencioso posible. Faltante de HELIUS_API_KEY o
SOLANA_KEYPAIR => RuntimeError al arrancar.
"""
from __future__ import annotations

from app.clients.blockchain_provider import IBlockchainProvider


class BlockchainConfigError(RuntimeError):
    """Falta configuración real de Solana (HELIUS_API_KEY o SOLANA_KEYPAIR)."""


def get_blockchain_provider() -> IBlockchainProvider:
    """Return the Helius blockchain provider.

    Raises:
        BlockchainConfigError: Si falta HELIUS_API_KEY o SOLANA_KEYPAIR.
    """
    from app.core.settings import get_settings

    settings = get_settings()

    missing = [
        name for name, val in (
            ("HELIUS_API_KEY", settings.HELIUS_API_KEY),
            ("SOLANA_KEYPAIR", settings.SOLANA_KEYPAIR),
        )
        if not val
    ]
    if missing:
        raise BlockchainConfigError(
            f"Blockchain real requiere {missing}. Setealos en el .env "
            "(CLAUDE.md #0.bis: simulacion eliminada, no hay fallback)."
        )

    from app.clients.helius_provider import HeliusProvider
    import httpx

    http = httpx.AsyncClient(timeout=settings.SOLANA_TIMEOUT)
    return HeliusProvider(
        api_key=settings.HELIUS_API_KEY,
        rpc_url=settings.effective_helius_rpc_url,
        http=http,
        keypair_raw=settings.SOLANA_KEYPAIR,
    )
