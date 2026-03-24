"""Purchase Order PDF generation using Jinja2 + WeasyPrint."""
from __future__ import annotations

from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class POPdfService:
    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
        )

    def generate_po_pdf(self, context: dict) -> bytes:
        """Render PO as PDF bytes."""
        template = self.env.get_template("po_order.html")
        html_str = template.render(**context)
        return HTML(string=html_str, base_url=str(TEMPLATES_DIR)).write_pdf()

    @staticmethod
    def build_context(
        po: dict,
        lines: list[dict],
        supplier: dict,
        tenant: dict,
    ) -> dict:
        """Build template context from PO data."""
        subtotal = sum(float(l.get("line_total", 0)) for l in lines)
        return {
            "po": po,
            "lines": lines,
            "supplier": supplier,
            "tenant": tenant,
            "subtotal": subtotal,
            "total": subtotal,
            "generated_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        }
