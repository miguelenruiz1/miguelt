"""Base adapter interface — all integrations must implement this."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Common interface for all external integrations."""

    provider_slug: str
    display_name: str

    @abstractmethod
    async def test_connection(self, credentials: dict) -> dict:
        """Test that the provided credentials are valid. Return {'ok': True} or raise."""
        ...

    @abstractmethod
    async def sync_products(self, credentials: dict, products: list[dict], direction: str = "push") -> list[dict]:
        """Sync products. direction: push (local→remote) or pull (remote→local)."""
        ...

    @abstractmethod
    async def sync_customers(self, credentials: dict, customers: list[dict], direction: str = "push") -> list[dict]:
        """Sync customers/third-parties."""
        ...

    @abstractmethod
    async def create_invoice(self, credentials: dict, invoice_data: dict) -> dict:
        """Create an electronic invoice on the remote platform."""
        ...

    @abstractmethod
    async def get_invoice(self, credentials: dict, remote_id: str) -> dict:
        """Retrieve an invoice by remote ID."""
        ...

    @abstractmethod
    async def list_invoices(self, credentials: dict, params: dict | None = None) -> list[dict]:
        """List recent invoices from the remote platform."""
        ...

    async def create_credit_note(self, credentials: dict, data: dict) -> dict:
        """Optional: create a credit note. Override if supported."""
        raise NotImplementedError(f"{self.provider_slug} does not support credit notes")

    async def process_webhook(self, payload: dict, headers: dict) -> dict:
        """Process an incoming webhook payload. Override per provider."""
        return {"status": "ignored", "reason": "no webhook handler"}
