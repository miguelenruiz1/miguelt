import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { drawLogo } from './pdfLogo'

export interface SandboxInvoicePDFData {
  company_name: string
  company_nit: string
  company_address?: string
  company_phone?: string
  company_email?: string

  customer_name: string
  customer_nit: string
  customer_email?: string
  customer_address?: string

  invoice_number: string
  invoice_date: string
  cufe: string

  items: {
    description: string
    quantity: number
    unit_price: number
    original_unit_price?: number | null
    price_source?: string | null
    discount_pct?: number
    tax_rate: number
    total: number
  }[]

  subtotal: number
  discount_pct?: number
  discount_amount?: number
  tax_amount: number
  total: number
  /** Total savings from special prices (sum of (original - actual) * qty) */
  special_price_savings?: number
}

function fmtCOP(n: number): string {
  return '$' + Math.round(n).toLocaleString('es-CO')
}

export function generateSandboxInvoicePDF(data: SandboxInvoicePDFData): void {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const pageW = doc.internal.pageSize.getWidth()
  const pageH = doc.internal.pageSize.getHeight()
  const margin = 20
  let y = margin

  // ── 1. HEADER ──────────────────────────────────────────────────────
  // Left: logo + company info
  drawLogo(doc, margin, y - 3, 12)
  doc.setFontSize(12)
  doc.setFont('helvetica', 'bold')
  doc.text(data.company_name, margin + 15, y)
  y += 5
  doc.setFontSize(8)
  doc.setFont('helvetica', 'normal')
  doc.text(`NIT: ${data.company_nit}`, margin, y)
  y += 3.5
  if (data.company_address) { doc.text(data.company_address, margin, y); y += 3.5 }
  if (data.company_phone) { doc.text(`Tel: ${data.company_phone}`, margin, y); y += 3.5 }
  if (data.company_email) { doc.text(data.company_email, margin, y); y += 3.5 }

  // Right: invoice title
  const rightX = pageW - margin
  doc.setFontSize(13)
  doc.setFont('helvetica', 'bold')
  doc.text('FACTURA ELECTRÓNICA DE VENTA', rightX, margin, { align: 'right' })
  doc.setFontSize(10)
  doc.text(`N° ${data.invoice_number}`, rightX, margin + 6, { align: 'right' })
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  doc.text(`Fecha: ${data.invoice_date}`, rightX, margin + 11, { align: 'right' })

  // ── 2. WATERMARK ───────────────────────────────────────────────────
  doc.saveGraphicsState()
  const gState = new (doc as any).GState({ opacity: 0.12 })
  doc.setGState(gState)
  doc.setTextColor(255, 0, 0)
  doc.setFontSize(72)
  doc.setFont('helvetica', 'bold')
  // Rotate 45° around page center
  const cx = pageW / 2
  const cy = pageH / 2
  const angle = 45
  const rad = (angle * Math.PI) / 180
  doc.text('SIMULADO', cx, cy, {
    align: 'center',
    angle,
  })
  doc.restoreGraphicsState()
  doc.setTextColor(0, 0, 0)

  // ── 3. CLIENT BOX ──────────────────────────────────────────────────
  y = Math.max(y, margin + 18) + 6
  const boxY = y
  doc.setDrawColor(180, 180, 180)
  doc.setLineWidth(0.3)
  doc.rect(margin, boxY, pageW - margin * 2, 24)
  y = boxY + 5
  doc.setFontSize(8)
  doc.setFont('helvetica', 'bold')
  doc.text('Facturar a:', margin + 4, y)
  y += 4
  doc.setFont('helvetica', 'normal')
  doc.text(`Nombre: ${data.customer_name}`, margin + 4, y); y += 3.5
  doc.text(`NIT: ${data.customer_nit}`, margin + 4, y); y += 3.5
  if (data.customer_email) { doc.text(`Email: ${data.customer_email}`, margin + 4, y); y += 3.5 }
  if (data.customer_address) { doc.text(`Dirección: ${data.customer_address}`, margin + 100, boxY + 9) }

  y = boxY + 28

  // ── 4. ITEMS TABLE ─────────────────────────────────────────────────
  const hasLineDiscount = data.items.some(item => (item.discount_pct ?? 0) > 0)

  const tableHead = hasLineDiscount
    ? [['Descripción', 'Cant.', 'Precio Unit.', 'Desc. %', 'IVA', 'Total']]
    : [['Descripción', 'Cant.', 'Precio Unit.', 'IVA', 'Total']]

  const tableBody = data.items.map(item => {
    let desc = item.description
    if (item.price_source === 'customer_special' && item.original_unit_price != null && item.original_unit_price > item.unit_price) {
      const pct = Math.round((1 - item.unit_price / item.original_unit_price) * 100)
      desc += `\n  Precio base: ${fmtCOP(item.original_unit_price)} → Especial (${pct}% dto.)`
    }
    const row = [
      desc,
      item.quantity.toString(),
      fmtCOP(item.unit_price),
    ]
    if (hasLineDiscount) row.push(item.discount_pct ? `${item.discount_pct}%` : '—')
    row.push(`${(item.tax_rate * 100).toFixed(0)}%`)
    row.push(fmtCOP(item.total))
    return row
  })

  const colStyles: Record<number, { halign?: string; cellWidth?: number | string }> = hasLineDiscount
    ? {
        0: { cellWidth: 'auto' },
        1: { halign: 'center', cellWidth: 18 },
        2: { halign: 'right', cellWidth: 28 },
        3: { halign: 'center', cellWidth: 18 },
        4: { halign: 'center', cellWidth: 16 },
        5: { halign: 'right', cellWidth: 28 },
      }
    : {
        0: { cellWidth: 'auto' },
        1: { halign: 'center', cellWidth: 20 },
        2: { halign: 'right', cellWidth: 30 },
        3: { halign: 'center', cellWidth: 18 },
        4: { halign: 'right', cellWidth: 30 },
      }

  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin },
    head: tableHead,
    body: tableBody,
    headStyles: {
      fillColor: [55, 55, 55],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 8,
    },
    bodyStyles: { fontSize: 8 },
    alternateRowStyles: { fillColor: [245, 245, 245] },
    columnStyles: colStyles as any,
  })

  y = (doc as any).lastAutoTable.finalY + 6

  // ── 5. TOTALS ──────────────────────────────────────────────────────
  const totalsX = pageW - margin
  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')

  // Show special price savings if any
  if (data.special_price_savings && data.special_price_savings > 0) {
    const originalTotal = data.subtotal + data.special_price_savings
    doc.setTextColor(100, 116, 139)
    doc.text(`Valor original (sin precios especiales):  ${fmtCOP(originalTotal)}`, totalsX, y, { align: 'right' })
    y += 5
    doc.setTextColor(16, 124, 65)
    doc.text(`Ahorro precios especiales:  -${fmtCOP(data.special_price_savings)}`, totalsX, y, { align: 'right' })
    y += 5
    doc.setTextColor(0, 0, 0)
  }

  doc.text(`Subtotal:  ${fmtCOP(data.subtotal)}`, totalsX, y, { align: 'right' })
  y += 5
  if (data.discount_pct && data.discount_pct > 0 && data.discount_amount) {
    doc.setTextColor(180, 100, 0)
    doc.text(`Descuento global (${data.discount_pct}%):  -${fmtCOP(data.discount_amount)}`, totalsX, y, { align: 'right' })
    y += 5
    doc.setTextColor(0, 0, 0)
    doc.text(`Base gravable:  ${fmtCOP(data.subtotal - data.discount_amount)}`, totalsX, y, { align: 'right' })
    y += 5
  }
  doc.text(`IVA:  ${fmtCOP(data.tax_amount)}`, totalsX, y, { align: 'right' })
  y += 6
  doc.setFontSize(12)
  doc.setFont('helvetica', 'bold')
  doc.text(`TOTAL:  ${fmtCOP(data.total)}`, totalsX, y, { align: 'right' })
  y += 10

  // ── 6. CUFE SECTION ────────────────────────────────────────────────
  doc.setDrawColor(160, 160, 160)
  doc.setLineDashPattern([2, 2], 0)
  doc.setLineWidth(0.3)
  const cufeBoxH = 18
  doc.rect(margin, y, pageW - margin * 2, cufeBoxH)
  doc.setLineDashPattern([], 0)

  doc.setFontSize(7)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(80, 80, 80)
  doc.text('CUFE (Código Único de Factura Electrónica)', margin + 3, y + 5)

  doc.setFont('courier', 'normal')
  doc.setFontSize(6.5)
  doc.setTextColor(40, 40, 40)
  doc.text(data.cufe, margin + 3, y + 10, { maxWidth: pageW - margin * 2 - 6 })

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(7)
  doc.setTextColor(220, 40, 40)
  doc.text('Este documento es una simulación. No tiene validez ante la DIAN.', margin + 3, y + 15)

  doc.setTextColor(0, 0, 0)
  y += cufeBoxH + 8

  // ── 7. FOOTER ──────────────────────────────────────────────────────
  const footerY = pageH - 12
  doc.setFontSize(7)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(140, 140, 140)
  doc.text('Generado por TraceLog — tracelog.co', margin, footerY)
  const now = new Date()
  doc.text(
    `Generado: ${now.toLocaleDateString('es-CO')} ${now.toLocaleTimeString('es-CO')}`,
    rightX, footerY, { align: 'right' },
  )

  // ── DOWNLOAD ───────────────────────────────────────────────────────
  const filename = `SIMULADO-${data.invoice_number}-${data.customer_nit}.pdf`
  doc.save(filename)
}
