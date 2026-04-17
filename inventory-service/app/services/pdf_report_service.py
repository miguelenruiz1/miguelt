"""Executive PDF report — P&L for non-technical business users."""
from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.enums import TA_RIGHT

# Colombia reports render to Bogota civil time and keep full Decimal precision
# for money. Earlier version forced float(value) which loses cents on large
# revenue (>2^53 COP) and drops decimal precision during accumulation.
_REPORT_TZ = ZoneInfo("America/Bogota")


def _cop(value) -> str:
    if value is None or value == "":
        return "$0"
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    rounded = d.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    sign = "-" if rounded < 0 else ""
    # `,` as thousand separator → swap to `.` (Colombia convention).
    formatted = f"{abs(rounded):,}".replace(",", ".")
    return f"{sign}${formatted}"


def _pct(value) -> str:
    if value is None or value == "":
        return "0.0%"
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return f"{d:.1f}%"


DARK = colors.HexColor("#1f2937")
GRAY = colors.HexColor("#6b7280")
LIGHT_GRAY = colors.HexColor("#f3f4f6")


def generate_pnl_pdf(pnl_data: dict, tenant_name: str = "TraceLog") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Title2", parent=styles["Title"], fontSize=18, textColor=DARK))
    styles.add(ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=12, textColor=GRAY))
    styles.add(ParagraphStyle("SectionHead", parent=styles["Heading2"], fontSize=14, textColor=DARK, spaceAfter=6))
    styles.add(ParagraphStyle("Question", parent=styles["Normal"], fontSize=11, textColor=DARK, fontName="Helvetica-Bold", spaceAfter=4))
    styles.add(ParagraphStyle("Answer", parent=styles["Normal"], fontSize=11, textColor=GRAY, spaceAfter=10))
    styles.add(ParagraphStyle("SmallRight", parent=styles["Normal"], fontSize=8, alignment=TA_RIGHT, textColor=GRAY))
    styles.add(ParagraphStyle("ProductTitle", parent=styles["Heading3"], fontSize=13, textColor=DARK, spaceBefore=12))

    elements = []
    totals = pnl_data.get("totals", {})
    products = pnl_data.get("products", [])

    elements.append(Paragraph(tenant_name, styles["Title2"]))
    elements.append(Paragraph("Reporte de Inventario y Rentabilidad", styles["Subtitle"]))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(f"Generado el {datetime.now(tz=_REPORT_TZ).strftime('%d/%m/%Y a las %H:%M')}", styles["SmallRight"]))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(HRFlowable(width="100%", thickness=1, color=GRAY))
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph("¿QUÉ COMPRAMOS?", styles["Question"]))
    elements.append(Paragraph(f"Compramos {totals.get('product_count', 0)} productos distintos por un total de <b>{_cop(totals.get('total_purchased_cost', 0))}</b>", styles["Answer"]))
    elements.append(Paragraph("¿QUÉ VENDIMOS?", styles["Question"]))
    elements.append(Paragraph(f"Ingresos totales por ventas: <b>{_cop(totals.get('total_revenue', 0))}</b>", styles["Answer"]))
    elements.append(Paragraph("¿CUÁNTO GANAMOS?", styles["Question"]))
    elements.append(Paragraph(f"Ganancia bruta: <b>{_cop(totals.get('gross_profit', 0))}</b> — margen del <b>{_pct(totals.get('gross_margin_pct', 0))}</b>", styles["Answer"]))
    elements.append(Paragraph("¿QUÉ TENEMOS EN BODEGA HOY?", styles["Question"]))
    elements.append(Paragraph(f"Inventario valorado en <b>{_cop(totals.get('stock_current_value', 0))}</b>", styles["Answer"]))

    elements.append(Spacer(1, 0.3*inch))
    kpi = [["Ingresos", "Costo ventas", "Utilidad bruta", "Margen"], [_cop(totals.get("total_revenue", 0)), _cop(totals.get("total_cogs", 0)), _cop(totals.get("gross_profit", 0)), _pct(totals.get("gross_margin_pct", 0))]]
    t = Table(kpi, colWidths=[3.5*cm]*4)
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), DARK), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 10), ("ALIGN", (0,0), (-1,-1), "CENTER"), ("GRID", (0,0), (-1,-1), 0.5, GRAY), ("BACKGROUND", (0,1), (-1,-1), LIGHT_GRAY), ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6)]))
    elements.append(t)

    for pnl in products:
        elements.append(PageBreak())
        s = pnl.get("summary", {})
        elements.append(Paragraph(f"{pnl['product_name']} ({pnl['product_sku']})", styles["ProductTitle"]))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
        elements.append(Spacer(1, 0.15*inch))
        result_data = [["Ingresos:", _cop(s.get("total_revenue", 0))], ["Costo real:", _cop(s.get("total_cogs", 0))], ["GANANCIA:", _cop(s.get("gross_profit", 0))], ["Margen logrado:", _pct(s.get("gross_margin_pct", 0))], ["Margen objetivo:", _pct(s.get("margin_target", 0))]]
        rt = Table(result_data, colWidths=[5*cm, 5*cm])
        rt.setStyle(TableStyle([("FONTSIZE", (0,0), (-1,-1), 10), ("FONTNAME", (0,2), (-1,2), "Helvetica-Bold"), ("ALIGN", (1,0), (1,-1), "RIGHT"), ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3), ("LINEBELOW", (0,1), (-1,1), 1, GRAY), ("LINEBELOW", (0,2), (-1,2), 2, DARK)]))
        elements.append(rt)

    if products:
        elements.append(PageBreak())
        elements.append(Paragraph("CONSOLIDADO GENERAL", styles["Title2"]))
        elements.append(HRFlowable(width="100%", thickness=1, color=GRAY))
        elements.append(Spacer(1, 0.2*inch))
        rows = [["Producto", "Ingresos", "Costo", "Utilidad", "Margen"]]
        for pnl in products:
            s = pnl["summary"]
            rows.append([pnl["product_name"][:30], _cop(s["total_revenue"]), _cop(s["total_cogs"]), _cop(s["gross_profit"]), _pct(s["gross_margin_pct"])])
        rows.append(["TOTAL", _cop(totals.get("total_revenue", 0)), _cop(totals.get("total_cogs", 0)), _cop(totals.get("gross_profit", 0)), _pct(totals.get("gross_margin_pct", 0))])
        ct = Table(rows, colWidths=[4.5*cm, 3*cm, 3*cm, 3*cm, 2.5*cm])
        ct.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), DARK), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9), ("GRID", (0,0), (-1,-1), 0.5, GRAY), ("ALIGN", (1,1), (-1,-1), "RIGHT"), ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"), ("BACKGROUND", (0,-1), (-1,-1), LIGHT_GRAY), ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))
        elements.append(ct)

    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("Reporte generado por TraceLog", styles["SmallRight"]))
    doc.build(elements)
    return buf.getvalue()
