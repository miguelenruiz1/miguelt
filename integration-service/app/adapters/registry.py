"""Adapter registry — maps provider_slug to adapter instance."""
from __future__ import annotations

from app.adapters.base import BaseAdapter
from app.adapters.matias import MatiasAdapter

_ADAPTERS: dict[str, BaseAdapter] = {
    "matias": MatiasAdapter(),
}

INTEGRATION_CATALOG = [
    {
        "slug": "matias",
        "name": "MATIAS API",
        "description": "Facturación electrónica Colombia (DIAN). Soporta modo producción y modo sandbox (pruebas).",
        "country": "CO",
        "category": "invoicing",
        "features": ["electronic_invoicing", "credit_notes", "debit_notes", "sandbox_mode"],
        "logo_url": None,
    },
]


def get_adapter(provider_slug: str) -> BaseAdapter | None:
    return _ADAPTERS.get(provider_slug)


def list_adapters() -> list[str]:
    return list(_ADAPTERS.keys())
