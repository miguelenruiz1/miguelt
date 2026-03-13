"""Sandbox adapter — simulates electronic invoicing without external calls."""
from __future__ import annotations

import hashlib
import time
import uuid

from app.adapters.base import BaseAdapter


class SandboxAdapter(BaseAdapter):
    provider_slug = "sandbox"
    display_name = "Sandbox — Simulación Facturación Electrónica"

    async def test_connection(self, credentials: dict) -> dict:
        return {"ok": True, "company_name": "Empresa Demo TraceLog"}

    async def create_invoice(self, credentials: dict, invoice_data: dict) -> dict:
        raw = str(invoice_data) + str(time.time())
        cufe = hashlib.sha384(raw.encode()).hexdigest()
        # Use resolution-assigned invoice number if available, else fallback to UUID
        inv_number = invoice_data.get("invoice_number") or str(uuid.uuid4())
        return {
            "remote_id": f"SANDBOX-{inv_number}",
            "invoice_number": inv_number,
            "cufe": cufe,
            "pdf_url": None,
            "qr_code": f"https://sandbox.tracelog.co/qr/{inv_number}",
            "status": "simulated",
            "simulated": True,
            "message": "Factura simulada — no tiene validez ante la DIAN",
        }

    async def get_invoice(self, credentials: dict, remote_id: str) -> dict:
        return {
            "remote_id": remote_id,
            "cufe": hashlib.sha384(remote_id.encode()).hexdigest(),
            "pdf_url": None,
            "qr_code": f"https://sandbox.tracelog.co/qr/{uuid.uuid4()}",
            "status": "simulated",
            "simulated": True,
            "message": "Factura simulada — no tiene validez ante la DIAN",
        }

    async def list_invoices(self, credentials: dict, params: dict | None = None) -> list[dict]:
        return {"items": [], "total": 0, "page": 1, "per_page": 20}

    async def create_credit_note(self, credentials: dict, data: dict) -> dict:
        raw = str(data) + str(time.time())
        cufe = hashlib.sha384(raw.encode()).hexdigest()
        cn_number = data.get("credit_note_number") or str(uuid.uuid4())
        return {
            "remote_id": f"SANDBOX-CN-{cn_number}",
            "credit_note_number": cn_number,
            "cufe": cufe,
            "pdf_url": None,
            "status": "simulated",
            "simulated": True,
            "message": "Nota crédito simulada — no tiene validez ante la DIAN",
        }

    async def sync_products(self, credentials: dict, products: list[dict], direction: str = "push") -> list[dict]:
        return []

    async def sync_customers(self, credentials: dict, customers: list[dict], direction: str = "push") -> list[dict]:
        return []
