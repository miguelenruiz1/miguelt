"""Invoice PDF rendering (FASE2 billing completeness).

Renders an enterprise-grade Colombian invoice PDF via WeasyPrint + Jinja2.
Computes IVA (19%) and falls back gracefully if weasyprint is unavailable
(e.g. dev environment without system libs) by returning a text/HTML fallback
only when explicitly asked — otherwise raises.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invoice
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.subscription_repo import SubscriptionRepository

log = structlog.get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "invoice_pdf" / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


# ─── Colombia tax lock ────────────────────────────────────────────────────────

IVA_RATE = Decimal("0.19")


def _fmt_money(amount: Decimal | float, currency: str = "COP") -> str:
    """Colombian-style currency formatting."""
    amt = Decimal(str(amount)).quantize(Decimal("0.01"))
    # Thousands separator = . , decimals = ,
    whole, _, dec = f"{amt:.2f}".partition(".")
    neg = whole.startswith("-")
    if neg:
        whole = whole[1:]
    grouped = f"{int(whole):,}".replace(",", ".")
    sign = "-" if neg else ""
    symbol = "$" if currency == "COP" else ""
    return f"{sign}{symbol}{grouped},{dec}"


@dataclass
class InvoiceContext:
    invoice: dict
    customer: dict
    line_items: list[dict]
    totals: dict
    pay_link: str


async def build_invoice_context(
    db: AsyncSession,
    invoice: Invoice,
    app_url: str = "http://localhost:3000",
    tenant_info: dict | None = None,
) -> InvoiceContext:
    """Populate the Jinja context for invoice.html from DB + tenant info."""
    sub_repo = SubscriptionRepository(db)
    sub = await sub_repo.get_by_id(invoice.subscription_id)

    # Normalize dates
    def _d(dt: datetime | date | None) -> str:
        if dt is None:
            return "—"
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d")
        return dt.isoformat()

    # Compute totals: amount stored is gross (business rule). Reverse-derive
    # subtotal and IVA for display: subtotal = amount / (1 + IVA_RATE).
    amount = Decimal(str(invoice.amount or 0))
    is_credit_note = (invoice.invoice_type or "standard") == "credit_note"
    subtotal = (amount / (Decimal("1") + IVA_RATE)).quantize(Decimal("0.01"))
    iva = (amount - subtotal).quantize(Decimal("0.01"))
    total = amount
    currency = invoice.currency or "COP"

    lines: list[dict] = []
    for raw in (invoice.line_items or []):
        unit = Decimal(str(raw.get("unit_price", 0)))
        ln_amount = Decimal(str(raw.get("amount", unit * Decimal(str(raw.get("quantity", 1))))))
        lines.append({
            "description": raw.get("description", ""),
            "quantity": raw.get("quantity", 1),
            "unit_price_fmt": _fmt_money(unit, currency),
            "amount_fmt": _fmt_money(ln_amount, currency),
        })
    if not lines:
        lines = [{
            "description": "Suscripción Trace",
            "quantity": 1,
            "unit_price_fmt": _fmt_money(amount, currency),
            "amount_fmt": _fmt_money(amount, currency),
        }]

    tenant_id = invoice.tenant_id
    info = tenant_info or {}
    customer = {
        "name": info.get("name") or f"Tenant {tenant_id}",
        "nit": info.get("nit"),
        "address": info.get("address"),
        "email": info.get("email"),
    }

    pay_link = f"{app_url}/checkout?invoice={invoice.id}"

    inv_dict = {
        "invoice_number": invoice.invoice_number,
        "invoice_type": invoice.invoice_type or "standard",
        "status": (invoice.status.value if hasattr(invoice.status, "value") else str(invoice.status)),
        "currency": currency,
        "issue_date": _d(invoice.created_at),
        "period_start": _d(invoice.period_start),
        "period_end": _d(invoice.period_end),
        "due_date": _d(invoice.due_date) if invoice.due_date else None,
        "notes": invoice.notes,
        "year": (invoice.created_at.year if invoice.created_at else datetime.now(timezone.utc).year),
    }

    totals = {
        "subtotal_fmt": _fmt_money(subtotal, currency),
        "iva_fmt": _fmt_money(iva, currency),
        "retefuente": None,
        "retefuente_fmt": None,
        "total_fmt": _fmt_money(total, currency),
    }

    return InvoiceContext(
        invoice=inv_dict,
        customer=customer,
        line_items=lines,
        totals=totals,
        pay_link=pay_link,
    )


def render_invoice_html(ctx: InvoiceContext) -> str:
    tmpl = _env.get_template("invoice.html")
    return tmpl.render(
        invoice=ctx.invoice,
        customer=ctx.customer,
        line_items=ctx.line_items,
        totals=ctx.totals,
        pay_link=ctx.pay_link,
    )


async def render_invoice_pdf(
    db: AsyncSession,
    invoice_id: str,
    app_url: str = "http://localhost:3000",
    tenant_info: dict | None = None,
) -> bytes:
    """Render a PDF for the given invoice_id and return raw bytes.

    Requires weasyprint (system libs: libpango, libcairo). If not available,
    raises RuntimeError — caller should surface a 503/501 to the client.
    """
    invoice_repo = InvoiceRepository(db)
    invoice = await invoice_repo.get_by_id(invoice_id)
    if invoice is None:
        raise ValueError(f"Invoice {invoice_id!r} not found")

    ctx = await build_invoice_context(db, invoice, app_url=app_url, tenant_info=tenant_info)
    html = render_invoice_html(ctx)

    try:
        from weasyprint import HTML  # type: ignore
    except Exception as exc:
        log.warning("weasyprint_unavailable", error=str(exc))
        raise RuntimeError(
            "weasyprint not available in this environment; install system libs "
            "(libpango, libcairo) or use an HTML fallback."
        ) from exc

    pdf_bytes = HTML(string=html, base_url=str(_TEMPLATE_DIR)).write_pdf()
    return pdf_bytes


def render_jinja(template_name: str, **context: Any) -> str:
    """Render any email template in templates/ dir."""
    tmpl = _env.get_template(template_name)
    return tmpl.render(**context)
