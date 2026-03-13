"""Schemas for integration service."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Config ──────────────────────────────────────────────────────────
class IntegrationConfigCreate(BaseModel):
    provider_slug: str
    display_name: str | None = None
    is_active: bool = False
    is_test_mode: bool = True
    simulation_mode: bool = True
    credentials: dict = {}
    extra_config: dict = {}
    sync_products: bool = False
    sync_customers: bool = False
    sync_invoices: bool = True


class IntegrationConfigUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None
    is_test_mode: bool | None = None
    simulation_mode: bool | None = None
    credentials: dict | None = None
    extra_config: dict | None = None
    sync_products: bool | None = None
    sync_customers: bool | None = None
    sync_invoices: bool | None = None


class IntegrationConfigOut(OrmBase):
    id: str
    tenant_id: str
    provider_slug: str
    display_name: str
    is_active: bool
    is_test_mode: bool
    simulation_mode: bool = True
    extra_config: dict
    sync_products: bool
    sync_customers: bool
    sync_invoices: bool
    last_sync_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ── Sync Jobs ───────────────────────────────────────────────────────
class SyncJobOut(OrmBase):
    id: str
    tenant_id: str
    integration_id: str
    provider_slug: str
    direction: str
    entity_type: str
    status: str
    total_records: int
    synced_records: int
    failed_records: int
    error_summary: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    triggered_by: str | None = None
    created_at: datetime | None = None


class PaginatedSyncJobs(BaseModel):
    items: list[SyncJobOut]
    total: int
    offset: int
    limit: int


# ── Sync Logs ───────────────────────────────────────────────────────
class SyncLogOut(OrmBase):
    id: str
    sync_job_id: str
    tenant_id: str
    entity_type: str
    local_id: str | None = None
    remote_id: str | None = None
    action: str
    status: str
    error_detail: str | None = None
    created_at: datetime | None = None


# ── Webhook Logs ────────────────────────────────────────────────────
class WebhookLogOut(OrmBase):
    id: str
    tenant_id: str | None = None
    provider_slug: str
    event_type: str | None = None
    payload: dict
    status: str
    processing_result: str | None = None
    created_at: datetime | None = None


class PaginatedWebhookLogs(BaseModel):
    items: list[WebhookLogOut]
    total: int
    offset: int
    limit: int


# ── Requests ────────────────────────────────────────────────────────
class SyncRequest(BaseModel):
    direction: str = "push"
    entity_type: str = "invoices"


class CreateInvoiceRequest(BaseModel):
    customer_tax_id: str
    lines: list[dict]
    notes: str | None = None
    send_to_dian: bool = True
    send_email: bool = True
    total: float = 0
    provider_document_id: int | None = None
    provider_payment_type_id: int | None = None
    date: str | None = None


class TestConnectionRequest(BaseModel):
    credentials: dict


# ── Invoice Resolutions ────────────────────────────────────────────
class InvoiceResolutionCreate(BaseModel):
    provider: str
    resolution_number: str
    prefix: str
    range_from: int
    range_to: int
    valid_from: date
    valid_to: date


class InvoiceResolutionOut(OrmBase):
    id: str
    tenant_id: str
    provider: str
    is_active: bool
    resolution_number: str
    prefix: str
    range_from: int
    range_to: int
    current_number: int
    valid_from: date
    valid_to: date
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Computed fields
    next_invoice_number: str = ""
    remaining: int = 0
    is_expired: bool = False
    is_exhausted: bool = False

    @model_validator(mode="after")
    def _compute_fields(self):
        self.next_invoice_number = f"{self.prefix}{self.current_number + 1}"
        self.remaining = max(0, self.range_to - self.current_number)
        self.is_expired = self.valid_to < date.today()
        self.is_exhausted = self.current_number >= self.range_to
        return self


# ── Credit Notes ──────────────────────────────────────────────────────
class CreateCreditNoteRequest(BaseModel):
    """Payload sent by inventory-service to create a credit note."""
    invoice_cufe: str
    invoice_number: str
    order_number: str
    date: str | None = None
    currency: str = "COP"
    reason: str = "Devolución de mercancía"
    customer: dict = {}
    items: list[dict] = []
    subtotal: float = 0
    tax_amount: float = 0
    total: float = 0


class CreditNoteResponse(BaseModel):
    remote_id: str = ""
    credit_note_number: str = ""
    cufe: str = ""
    pdf_url: str | None = None
    status: str = ""
    simulated: bool = False
