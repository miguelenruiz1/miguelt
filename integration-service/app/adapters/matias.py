"""MATIAS API v2 adapter — electronic invoicing for Colombia (DIAN).

MATIAS API v2 docs: https://api-v2.matias-api.com
Auth: Bearer JWT token (Personal Access Token)
Format: UBL 2.1 Colombia
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx

from app.adapters.base import BaseAdapter
from app.core.errors import AdapterError

MATIAS_BASE_URL = "https://api-v2.matias-api.com/api/ubl2.1"

# Colombia timezone (UTC-5)
COL_TZ_OFFSET = timezone(timedelta(hours=-5))


class MatiasAdapter(BaseAdapter):
    provider_slug = "matias"
    display_name = "MATIAS API — Facturación Electrónica DIAN"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=False)

    def _headers(self, credentials: dict) -> dict:
        api_key = credentials.get("api_key", "")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
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
            raise AdapterError("matias", f"MATIAS API error {resp.status_code}: {resp.text[:500]}", resp.status_code)

        return resp.json() if resp.content else {}

    # ── Interface Implementation ────────────────────────────────────

    async def test_connection(self, credentials: dict) -> dict:
        if self._is_simulation(credentials):
            return {"ok": True, "provider": "matias", "message": "Simulation mode — no real connection", "simulation": True}
        # Use a simple GET to verify auth
        try:
            headers = self._headers(credentials)
            resp = await self._client.get(f"{MATIAS_BASE_URL}/config/software", headers=headers)
            if resp.status_code == 200:
                return {"ok": True, "provider": "matias", "message": "Conexión exitosa con MATIAS API v2"}
            if resp.status_code == 401:
                return {"ok": False, "provider": "matias", "message": "Token inválido o expirado"}
            return {"ok": True, "provider": "matias", "message": f"MATIAS API responde (HTTP {resp.status_code})"}
        except httpx.RequestError as e:
            return {"ok": False, "provider": "matias", "message": f"Error de conexión: {e}"}

    async def sync_products(self, credentials: dict, products: list[dict], direction: str = "push") -> list[dict]:
        return []

    async def sync_customers(self, credentials: dict, customers: list[dict], direction: str = "push") -> list[dict]:
        return []

    async def create_invoice(self, credentials: dict, invoice_data: dict) -> dict:
        if self._is_simulation(credentials):
            return self._simulated_invoice(invoice_data)

        payload = self._build_invoice_payload(invoice_data)
        resp = await self._request("POST", "/invoice", credentials, json=payload)
        inv_number = invoice_data.get("invoice_number") or resp.get("number", "")
        return {
            "remote_id": str(resp.get("id", "")),
            "invoice_number": inv_number,
            "cufe": resp.get("cufe", resp.get("uuid", "")),
            "pdf_url": resp.get("pdf_url", resp.get("urlinvoicepdf", "")),
            "qr_code": resp.get("qr_code", resp.get("urlqrcode", "")),
            "status": "issued" if resp.get("status_code") in (None, "1", 1) else resp.get("status_description", "issued"),
            "raw_response": resp,
        }

    async def get_invoice(self, credentials: dict, remote_id: str) -> dict:
        if self._is_simulation(credentials):
            return {"remote_id": remote_id, "status": "simulated"}
        return await self._request("GET", f"/invoice/{remote_id}", credentials)

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
        resp = await self._request("POST", "/credit-note", credentials, json=payload)
        return {
            "remote_id": str(resp.get("id", "")),
            "credit_note_number": data.get("credit_note_number", resp.get("number", "")),
            "cufe": resp.get("cufe", resp.get("uuid", "")),
            "pdf_url": resp.get("pdf_url", resp.get("urlinvoicepdf", "")),
            "status": "issued",
        }

    async def process_webhook(self, payload: dict, headers: dict) -> dict:
        event_type = payload.get("event", "unknown")
        return {"status": "processed", "event_type": event_type, "invoice_id": payload.get("invoice_id")}

    # ── Helpers ─────────────────────────────────────────────────────

    def _simulated_invoice(self, invoice_data: dict) -> dict:
        sim_id = uuid.uuid4().hex[:12]
        return {
            "remote_id": f"SIM-{sim_id}",
            "invoice_number": invoice_data.get("invoice_number", ""),
            "cufe": f"SIMULATED-CUFE-{uuid.uuid4().hex}",
            "pdf_url": "",
            "qr_code": "",
            "status": "simulated",
        }

    @staticmethod
    def _clean_dni(value: str) -> str:
        """Strip non-alphanumeric chars from DNI/NIT."""
        import re
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', str(value or "").strip())
        return cleaned or "222222222"

    @staticmethod
    def _calc_due_date(data: dict) -> str:
        """Calculate payment due date from date + payment_terms_days."""
        if data.get("due_date"):
            return data["due_date"]
        base_date = data.get("date", datetime.now(COL_TZ_OFFSET).strftime("%Y-%m-%d"))
        terms = data.get("payment_terms_days", 0) or 0
        if terms > 0:
            from datetime import timedelta
            d = datetime.strptime(base_date, "%Y-%m-%d")
            return (d + timedelta(days=terms)).strftime("%Y-%m-%d")
        return base_date

    def _build_customer(self, customer: dict) -> dict:
        """Build UBL 2.1 customer from Trace customer data with smart defaults."""
        doc_type = customer.get("document_type", "CC")
        nit = self._clean_dni(customer.get("nit") or customer.get("tax_id"))

        # Map Trace document_type → Matias type_document_identification_id
        DOC_TYPE_MAP = {"CC": 6, "NIT": 9, "CE": 2, "PP": 7, "TI": 5, "RC": 4}
        type_doc_id = DOC_TYPE_MAP.get(doc_type, 6)

        # Smart defaults by document type
        if doc_type == "NIT":
            org_type = customer.get("organization_type", 1)  # Jurídica
            regime = customer.get("tax_regime", 1)  # Responsable IVA
            liability = customer.get("tax_liability", 7)
        else:
            org_type = customer.get("organization_type", 2)  # Persona Natural
            regime = customer.get("tax_regime", 2)  # No responsable IVA
            liability = customer.get("tax_liability", 7)  # No aplica

        # Address extraction — prefer flat fields, fallback to nested address dict
        addr = customer.get("address", {}) or {}
        addr_line = customer.get("address_line") or addr.get("line1", "")
        city = customer.get("city") or addr.get("city", "")

        # Build full address string for Matias
        full_address = addr_line
        if city and addr_line:
            full_address = f"{addr_line}, {city}"
        elif city:
            full_address = city

        # Resolve municipality_id from city name if default (149)
        from app.data.municipalities import resolve_municipality_id
        raw_municipality = customer.get("municipality_id", 149)
        if raw_municipality == 149 and city:
            raw_municipality = resolve_municipality_id(city)

        result = {
            "identification_number": nit,
            "dni": nit,
            "dv": str(customer.get("dv", "0") or "0"),
            "name": customer.get("name", "Cliente"),
            "company_name": customer.get("company_name") or customer.get("name", "Cliente"),
            "email": customer.get("email", ""),
            "phone": customer.get("phone", ""),
            "address": full_address or "Sin dirección",
            "municipality_id": raw_municipality,
            "type_document_identification_id": type_doc_id,
            "type_organization_id": org_type,
            "type_regime_id": regime,
            "type_liability_id": liability,
        }
        return result

    def _build_invoice_payload(self, data: dict) -> dict:
        """Build MATIAS API v2 UBL 2.1 compatible payload."""
        resolution = data.get("resolution", {})
        customer = data.get("customer", {})

        # Build line items in Matias UBL 2.1 format
        invoice_lines = []
        for i, line in enumerate(data.get("items", data.get("lines", [])), 1):
            tax_rate = float(line.get("tax_rate", 0))
            unit_price = float(line.get("unit_price", 0))
            quantity = float(line.get("quantity", line.get("qty_shipped", 1)))
            discount_rate = float(line.get("discount_rate", line.get("discount_pct", 0) / 100 if line.get("discount_pct") else 0))
            line_subtotal = round(unit_price * quantity * (1 - discount_rate), 2)
            tax_amount = round(line_subtotal * tax_rate / 100, 2)

            invoice_lines.append({
                "quantity_units_id": 70,  # UN (unidad)
                "invoiced_quantity": str(quantity),
                "line_extension_amount": f"{line_subtotal:.2f}",
                "free_of_charge_indicator": False,
                "description": line.get("description", line.get("product_name", line.get("name", "Producto"))),
                "code": line.get("sku", line.get("code", f"PROD-{i}")),
                "type_item_identifications_id": 4,  # Estándar de adopción del contribuyente
                "price_amount": f"{unit_price:.2f}",
                "base_quantity": str(quantity),
                "tax_totals": [{
                    "tax_id": 1,  # IVA
                    "percent": f"{tax_rate:.2f}",
                    "tax_amount": f"{tax_amount:.2f}",
                    "taxable_amount": f"{line_subtotal:.2f}",
                }] if tax_rate > 0 else [],
            })

        # Calculate totals
        subtotal = float(data.get("subtotal", data.get("subtotal_after_discount", 0)))
        tax_amount = float(data.get("tax_amount", 0))
        total = float(data.get("total", subtotal + tax_amount))
        total_retention = float(data.get("total_retention", 0))
        total_payable = float(data.get("total_payable", total - total_retention))

        payload = {
            "type_document_id": 7,  # Factura electrónica de venta (sandbox/habilitación)
            "operation_type_id": 10,  # Estándar
            "resolution_number": resolution.get("resolution_number", data.get("resolution_number", "")),
            "prefix": resolution.get("prefix", "SETP"),
            "number": data.get("invoice_number", ""),
            "document_number": int("".join(c for c in str(data.get("invoice_number", "0")) if c.isdigit()) or "0"),
            "date": data.get("date", datetime.now(COL_TZ_OFFSET).strftime("%Y-%m-%d")),
            "time": datetime.now(COL_TZ_OFFSET).strftime("%H:%M:%S"),
            "customer": self._build_customer(customer),
            "legal_monetary_totals": {
                "line_extension_amount": f"{subtotal:.2f}",
                "tax_exclusive_amount": f"{subtotal:.2f}",
                "tax_inclusive_amount": f"{total:.2f}",
                "payable_amount": f"{total_payable:.2f}",
            },
            "tax_totals": [{
                "tax_id": 1,
                "percent": "19.00",
                "tax_amount": f"{tax_amount:.2f}",
                "taxable_amount": f"{subtotal:.2f}",
            }] if tax_amount > 0 else [],
            "withholding_tax_totals": [{
                "tax_id": 6,  # Retención en la fuente
                "percent": f"{(total_retention / subtotal * 100):.2f}" if subtotal > 0 and total_retention > 0 else "0.00",
                "tax_amount": f"{total_retention:.2f}",
                "taxable_amount": f"{subtotal:.2f}",
            }] if total_retention > 0 else [],
            "payments": [{
                "payment_form_id": data.get("payment_form", 1),
                "payment_method_id": 1,
                "means_payment_id": data.get("payment_method", 10),
                "payment_due_date": self._calc_due_date(data),
                "value_paid": f"{total_payable:.2f}",
            }],
            "lines": invoice_lines,
            "notes": data.get("notes", ""),
        }

        return payload

    def _build_credit_note_payload(self, data: dict) -> dict:
        """Build MATIAS API v2 credit note payload."""
        resolution = data.get("resolution", {})
        customer = data.get("customer", {})

        invoice_lines = []
        for i, line in enumerate(data.get("items", []), 1):
            unit_price = float(line.get("unit_price", 0))
            quantity = float(line.get("quantity", 1))
            line_subtotal = round(unit_price * quantity, 2)
            tax_rate = float(line.get("tax_rate", 0))
            tax_amount = round(line_subtotal * tax_rate / 100, 2)

            invoice_lines.append({
                "unit_measure_id": 70,
                "invoiced_quantity": str(quantity),
                "line_extension_amount": f"{line_subtotal:.2f}",
                "description": line.get("description", line.get("product_name", "Producto")),
                "code": line.get("sku", f"PROD-{i}"),
                "type_item_identification_id": 4,
                "price_amount": f"{unit_price:.2f}",
                "base_quantity": str(quantity),
                "tax_totals": [{
                    "tax_id": 1,
                    "percent": f"{tax_rate:.2f}",
                    "tax_amount": f"{tax_amount:.2f}",
                    "taxable_amount": f"{line_subtotal:.2f}",
                }] if tax_rate > 0 else [],
            })

        subtotal = float(data.get("subtotal", 0))
        tax_amount = float(data.get("tax_amount", 0))
        total = float(data.get("total", subtotal + tax_amount))

        return {
            "type_document_id": 4,  # Nota crédito
            "resolution_number": resolution.get("resolution_number", ""),
            "prefix": resolution.get("prefix", "NC"),
            "number": data.get("credit_note_number", ""),
            "date": data.get("date", datetime.now(COL_TZ_OFFSET).strftime("%Y-%m-%d")),
            "time": datetime.now(COL_TZ_OFFSET).strftime("%H:%M:%S"),
            "billing_reference": {
                "number": data.get("invoice_number", ""),
                "uuid": data.get("invoice_cufe", ""),
                "issue_date": data.get("invoice_date", ""),
            },
            "discrepancy_response": {
                "correction_concept_id": 2,  # Devolución
                "description": data.get("reason", "Devolución de mercancía"),
            },
            "customer": {
                "identification_number": customer.get("nit", customer.get("tax_id", "")),
                "name": customer.get("name", ""),
                "email": customer.get("email", ""),
                "municipality_id": 149,
            },
            "legal_monetary_totals": {
                "line_extension_amount": f"{subtotal:.2f}",
                "tax_exclusive_amount": f"{subtotal:.2f}",
                "tax_inclusive_amount": f"{total:.2f}",
                "payable_amount": f"{total:.2f}",
            },
            "tax_totals": [{
                "tax_id": 1,
                "percent": "19.00",
                "tax_amount": f"{tax_amount:.2f}",
                "taxable_amount": f"{subtotal:.2f}",
            }] if tax_amount > 0 else [],
            "payments": [{
                "payment_form_id": 1,
                "payment_method_id": 10,
                "payment_due_date": data.get("date", datetime.now(COL_TZ_OFFSET).strftime("%Y-%m-%d")),
            }],
            "lines": invoice_lines,
        }
