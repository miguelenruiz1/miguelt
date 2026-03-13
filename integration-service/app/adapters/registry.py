"""Adapter registry — maps provider_slug to adapter instance."""
from __future__ import annotations

from app.adapters.base import BaseAdapter
from app.adapters.matias import MatiasAdapter
from app.adapters.sandbox import SandboxAdapter

# Register adapters here as they're created
_ADAPTERS: dict[str, BaseAdapter] = {
    "matias": MatiasAdapter(),
    "sandbox": SandboxAdapter(),
}

# Catalog of available integrations (shown in marketplace)
INTEGRATION_CATALOG = [
    {
        "slug": "matias",
        "name": "MATIAS API",
        "description": "Facturación electrónica Colombia (DIAN). Emite facturas válidas desde tus Sales Orders.",
        "country": "CO",
        "category": "invoicing",
        "features": ["electronic_invoicing", "credit_notes"],
        "logo_url": None,
    },
    {
        "slug": "sandbox",
        "name": "Sandbox — Simulación",
        "description": "Simula facturación electrónica sin conexión a la DIAN. Ideal para demos y onboarding.",
        "country": "CO",
        "category": "invoicing",
        "features": ["electronic_invoicing_sandbox", "credit_notes_sandbox"],
        "logo_url": None,
    },
]


def get_adapter(provider_slug: str) -> BaseAdapter | None:
    return _ADAPTERS.get(provider_slug)


def list_adapters() -> list[str]:
    return list(_ADAPTERS.keys())
