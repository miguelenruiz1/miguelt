"""MATIAS API adapter — electronic invoicing for Colombia (DIAN).

MATIAS API docs: https://api.matias-api.com/v1
Auth: Bearer token per tenant (API key)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx

from app.adapters.base import BaseAdapter
from app.core.errors import AdapterError

MATIAS_BASE_URL = "https://api.matias-api.com/v1"


class MatiasAdapter(BaseAdapter):
    provider_slug = "matias"
    display_name = "MATIAS API — Facturación Electrónica DIAN"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    def _headers(self, credentials: dict) -> dict:
        api_key = credentials.get("api_key", "")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _is_simulation(self, credentials: dict) -> bool:
        return credentials.get("simulation_mode", False)

    async def _request(self, method: str, path: str, credentials: dict, **kwargs) -> dict:
        headers = self._headers(credentials)
        try:
            resp = await self._client.request(
                method, f"{MATIAS_BASE_URL}{path}", headers=headers, **kwargs
            )
        except httpx.RequestError as e:
            raise AdapterError("matias", f"Connection error: {e}")

        if resp.status_code >= 400:
            raise AdapterError("matias", f"MATIAS API error {resp.status_code}: {resp.text}", resp.status_code)

        return resp.json() if resp.content else {}

    # ── Interface Implementation ────────────────────────────────────

    async def test_connection(self, credentials: dict) -> dict:
        if self._is_simulation(credentials):
            return {"ok": True, "provider": "matias", "message": "Simulation mode — no real connection", "simulation": True}
        resp = await self._request("GET", "/account", credentials)
        return {
            "ok": True,
            "provider": "matias",
            "company_name": resp.get("company_name", ""),
            "message": "Authentication successful",
        }

    async def sync_products(self, credentials: dict, products: list[dict], direction: str = "push") -> list[dict]:
        # MATIAS is invoicing-only; product sync not applicable
        return []

    async def sync_customers(self, credentials: dict, customers: list[dict], direction: str = "push") -> list[dict]:
        # MATIAS is invoicing-only; customer sync not applicable
        return []

    async def create_invoice(self, credentials: dict, invoice_data: dict) -> dict:
        if self._is_simulation(credentials):
            return self._simulated_invoice(invoice_data)

        payload = self._build_invoice_payload(invoice_data)
        resp = await self._request("POST", "/invoices", credentials, json=payload)
        inv_number = invoice_data.get("invoice_number") or resp.get("number", "")
        return {
            "remote_id": resp.get("id", ""),
            "invoice_number": inv_number,
            "cufe": resp.get("document_key", ""),
            "pdf_url": resp.get("pdf_url", ""),
            "qr_code": resp.get("qr_code", ""),
            "status": resp.get("status", "issued"),
            "raw_response": resp,
        }

    async def get_invoice(self, credentials: dict, remote_id: str) -> dict:
        if self._is_simulation(credentials):
            return {"remote_id": remote_id, "status": "simulated"}
        return await self._request("GET", f"/invoices/{remote_id}", credentials)

    async def list_invoices(self, credentials: dict, params: dict | None = None) -> list[dict]:
        if self._is_simulation(credentials):
            return []
        query = {"page": 1, "per_page": 25}
        if params:
            query.update(params)
        resp = await self._request("GET", "/invoices", credentials, params=query)
        return resp.get("results", resp.get("data", []))

    async def create_credit_note(self, credentials: dict, data: dict) -> dict:
        if self._is_simulation(credentials):
            return {
                "remote_id": f"SIM-CN-{uuid.uuid4().hex[:8]}",
                "credit_note_number": data.get("credit_note_number", ""),
                "cufe": f"SIMULATED-CUFE-{uuid.uuid4().hex}",
                "status": "simulated",
                "simulated": True,
            }
        payload = self._build_credit_note_payload(data)
        resp = await self._request("POST", "/credit-notes", credentials, json=payload)
        return {
            "remote_id": resp.get("id", ""),
            "credit_note_number": data.get("credit_note_number", resp.get("number", "")),
            "cufe": resp.get("cufe", ""),
            "pdf_url": resp.get("pdf_url"),
            "status": resp.get("status", "created"),
        }

    async def process_webhook(self, payload: dict, headers: dict) -> dict:
        event_type = payload.get("event", "unknown")
        return {
            "status": "processed",
            "event_type": event_type,
            "invoice_id": payload.get("invoice_id"),
        }

    # ── Helpers ─────────────────────────────────────────────────────

    def _simulated_invoice(self, invoice_data: dict) -> dict:
        sim_id = uuid.uuid4().hex[:12]
        return {
            "remote_id": f"SIM-{sim_id}",
            "cufe": f"SIMULATED-CUFE-{uuid.uuid4().hex}",
            "pdf_url": "",
            "qr_code": "",
            "status": "simulated",
        }

    def _build_invoice_payload(self, data: dict) -> dict:
        """Build MATIAS API UBL 2.1 compatible payload."""
        items = []
        for line in data.get("items", data.get("lines", [])):
            items.append({
                "code": line.get("sku", ""),
                "description": line.get("name", line.get("product_name", "")),
                "quantity": line.get("quantity", line.get("qty_shipped", 1)),
                "unit_price": line.get("unit_price", 0),
                "discount_percent": line.get("discount_pct", 0),
                "tax_rate": line.get("tax_rate", 0),
            })

        customer = data.get("customer", {})
        payload = {
            "number": data.get("invoice_number", data.get("number", "")),
            "date": data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "due_date": data.get("due_date"),
            "currency": data.get("currency", "COP"),
            "customer": {
                "identification": customer.get("nit", customer.get("tax_id", "")),
                "name": customer.get("name", ""),
                "email": customer.get("email", ""),
                "address": customer.get("address", ""),
                "city": customer.get("city", ""),
                "phone": customer.get("phone", ""),
            },
            "items": items,
            "subtotal": data.get("subtotal", 0),
            "tax_amount": data.get("tax_amount", 0),
            "total": data.get("total", 0),
            "notes": data.get("notes", ""),
        }
        # Include resolution numbering range if provided
        resolution = data.get("resolution")
        if resolution:
            payload["numbering_range"] = resolution
        return payload

    def _build_credit_note_payload(self, data: dict) -> dict:
        """Build MATIAS API credit note payload with billing reference."""
        items = []
        for line in data.get("items", []):
            items.append({
                "code": line.get("sku", ""),
                "description": line.get("description", line.get("product_name", "")),
                "quantity": line.get("quantity", 1),
                "unit_price": line.get("unit_price", 0),
                "discount_percent": line.get("discount_pct", 0),
                "tax_rate": line.get("tax_rate", 0),
            })

        customer = data.get("customer", {})
        payload = {
            "number": data.get("credit_note_number", ""),
            "date": data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "currency": data.get("currency", "COP"),
            "type": "credit_note",
            "billing_reference": {
                "number": data.get("invoice_number", ""),
                "cufe": data.get("invoice_cufe", ""),
            },
            "discrepancy_response": {
                "code": "2",
                "description": data.get("reason", "Devolución de mercancía"),
            },
            "customer": {
                "identification": customer.get("nit", customer.get("tax_id", "")),
                "name": customer.get("name", ""),
                "email": customer.get("email", ""),
            },
            "items": items,
            "subtotal": data.get("subtotal", 0),
            "tax_amount": data.get("tax_amount", 0),
            "total": data.get("total", 0),
        }
        resolution = data.get("resolution")
        if resolution:
            payload["numbering_range"] = resolution
        return payload
