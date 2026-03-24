"""PDF rendering via Jinja2 + WeasyPrint."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.logging import get_logger

log = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _build_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def render_certificate_pdf(context: dict) -> bytes:
    """Render a certificate PDF from HTML template.

    Selects template by framework slug: tries ``certificate_{slug}.html``
    first, then falls back to ``certificate_base.html``.

    Returns raw PDF bytes.
    """
    env = _build_env()
    slug = context.get("framework", {}).get("slug", "base")
    template_name = f"certificate_{slug}.html"

    try:
        template = env.get_template(template_name)
    except Exception:
        log.info("template_fallback", attempted=template_name, using="certificate_base.html")
        template = env.get_template("certificate_base.html")

    html = template.render(**context)

    from weasyprint import HTML

    pdf_bytes = HTML(
        string=html,
        base_url=str(TEMPLATES_DIR),
    ).write_pdf()

    log.info("pdf_rendered", size=len(pdf_bytes), template=template_name)
    return pdf_bytes
