import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { drawLogo } from './pdfLogo'

export interface RemissionData {
  remission_number: string
  remission_date: string | null
  shipped_at: string | null

  company: {
    name: string
    nit: string
    address: string
    phone: string
    email: string
  }

  customer: {
    name: string
    nit: string
    address: string
    phone: string
    email: string
    contact_name: string
  }

  warehouse: {
    name: string
    address: string
    city: string
  }

  so_number: string
  invoice_number: string | null
  notes: string | null

  lines: {
    product_name: string
    product_code: string
    quantity: number
    unit: string
    warehouse_name: string
    lot_number: string | null
    serial_number: string | null
    unit_price: number
    discount_pct: number
    line_subtotal: number
    line_total: number
    tax_rate: number
    tax_amount: number
  }[]

  total_items: number
  total_quantity: number
  subtotal: number
  total_discount: number
  total_tax: number
  grand_total: number
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '--'
  return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' })
}

function fmtDateTime(): string {
  return new Date().toLocaleString('es-CO', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function fmtMoney(v: number): string {
  return '$' + v.toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

export function generateRemissionPDF(data: RemissionData): void {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const pageW = doc.internal.pageSize.getWidth()
  const pageH = doc.internal.pageSize.getHeight()
  const margin = 15
  const contentW = pageW - margin * 2
  let y = margin

  // ── 1. HEADER ──────────────────────────────────────────────────────
  // Left: company info
  // Logo
  drawLogo(doc, margin, y + 1, 14)

  // Company name
  doc.setFontSize(16)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text(data.company.name, margin + 18, y + 6)

  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(100, 116, 139)
  let compY = y + 11
  if (data.company.nit) { doc.text(`NIT: ${data.company.nit}`, margin + 18, compY); compY += 4 }
  if (data.company.address) { doc.text(data.company.address, margin + 18, compY); compY += 4 }
  const compContact = [data.company.phone, data.company.email].filter(Boolean).join(' | ')
  if (compContact) { doc.text(compContact, margin + 18, compY) }

  // Right: Remission box
  const boxW = 72
  const boxX = pageW - margin - boxW
  const boxH = 36
  doc.setDrawColor(203, 213, 225)
  doc.setLineWidth(0.5)
  doc.roundedRect(boxX, y, boxW, boxH, 2, 2, 'S')

  doc.setFontSize(11)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('REMISIÓN DE ENTREGA', boxX + boxW / 2, y + 7, { align: 'center' })

  doc.setFontSize(18)
  doc.setTextColor(220, 38, 38)
  doc.text(data.remission_number, boxX + boxW / 2, y + 15, { align: 'center' })

  doc.setFontSize(8)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(100, 116, 139)
  doc.text(`Fecha: ${fmtDate(data.remission_date)}`, boxX + boxW / 2, y + 21, { align: 'center' })
  doc.text(`Ref. SO: ${data.so_number}`, boxX + boxW / 2, y + 26, { align: 'center' })
  doc.text(`Ref. Factura: ${data.invoice_number || 'Pendiente'}`, boxX + boxW / 2, y + 31, { align: 'center' })

  y += Math.max(boxH, 24) + 6

  // ── 2. RECIPIENT ──────────────────────────────────────────────────
  doc.setDrawColor(203, 213, 225)
  doc.setLineWidth(0.3)
  const recipH = 30
  doc.roundedRect(margin, y, contentW, recipH, 2, 2, 'S')

  doc.setFontSize(9)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('Entregar a:', margin + 4, y + 6)

  doc.setFont('helvetica', 'normal')
  doc.setTextColor(51, 65, 85)
  let ry = y + 12
  const leftCol = margin + 4
  const rightCol = margin + contentW / 2
  if (data.customer.name) { doc.text(`Empresa: ${data.customer.name}`, leftCol, ry) }
  if (data.customer.nit) { doc.text(`NIT: ${data.customer.nit}`, rightCol, ry) }
  ry += 5
  if (data.customer.contact_name) { doc.text(`Contacto: ${data.customer.contact_name}`, leftCol, ry) }
  if (data.customer.phone) { doc.text(`Tel: ${data.customer.phone}`, rightCol, ry) }
  ry += 5
  if (data.customer.address) { doc.text(`Dir: ${data.customer.address}`, leftCol, ry) }

  y += recipH + 5

  // ── 3. DISPATCH INFO (3 boxes) ─────────────────────────────────────
  const boxW3 = (contentW - 6) / 3
  const boxH3 = 18

  // Box 1: Warehouse
  doc.setFillColor(248, 250, 252)
  doc.roundedRect(margin, y, boxW3, boxH3, 2, 2, 'F')
  doc.setFontSize(7)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(100, 116, 139)
  doc.text('BODEGA ORIGEN', margin + 3, y + 5)
  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(15, 23, 42)
  doc.text(data.warehouse.name, margin + 3, y + 10)
  doc.setFontSize(7)
  doc.setTextColor(100, 116, 139)
  const whAddr = [data.warehouse.address, data.warehouse.city].filter(Boolean).join(', ')
  if (whAddr) doc.text(whAddr, margin + 3, y + 14)

  // Box 2: Ship date
  const bx2 = margin + boxW3 + 3
  doc.setFillColor(248, 250, 252)
  doc.roundedRect(bx2, y, boxW3, boxH3, 2, 2, 'F')
  doc.setFontSize(7)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(100, 116, 139)
  doc.text('FECHA DESPACHO', bx2 + 3, y + 5)
  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(15, 23, 42)
  doc.text(fmtDate(data.shipped_at), bx2 + 3, y + 10)

  // Box 3: Totals
  const bx3 = margin + (boxW3 + 3) * 2
  doc.setFillColor(248, 250, 252)
  doc.roundedRect(bx3, y, boxW3, boxH3, 2, 2, 'F')
  doc.setFontSize(7)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(100, 116, 139)
  doc.text('TOTAL BULTOS', bx3 + 3, y + 5)
  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(15, 23, 42)
  doc.text(`${data.total_items} ítems / ${data.total_quantity} unidades`, bx3 + 3, y + 10)

  y += boxH3 + 6

  // ── 4. PRODUCTS TABLE ──────────────────────────────────────────────
  const tableBody = data.lines.map((l, i) => [
    String(i + 1),
    l.product_code || '—',
    l.product_name,
    String(l.quantity),
    l.unit,
    fmtMoney(l.unit_price),
    l.discount_pct > 0 ? `${l.discount_pct}%` : '—',
    fmtMoney(l.line_total),
  ])

  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin },
    head: [['#', 'Código', 'Producto', 'Cant.', 'Und', 'P. Unit.', 'Desc.', 'Total']],
    body: tableBody,
    headStyles: {
      fillColor: [30, 41, 59],
      textColor: [255, 255, 255],
      fontSize: 8,
      fontStyle: 'bold',
      halign: 'left',
    },
    bodyStyles: {
      fontSize: 8,
      textColor: [51, 65, 85],
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252],
    },
    columnStyles: {
      0: { cellWidth: 8, halign: 'center' },
      1: { cellWidth: 20 },
      2: { cellWidth: 'auto' },
      3: { cellWidth: 14, halign: 'right' },
      4: { cellWidth: 12 },
      5: { cellWidth: 22, halign: 'right' },
      6: { cellWidth: 14, halign: 'center' },
      7: { cellWidth: 24, halign: 'right', fontStyle: 'bold' },
    },
    didDrawPage: () => {
      // Footer on each page
      doc.setFontSize(7)
      doc.setFont('helvetica', 'italic')
      doc.setTextColor(156, 163, 175)
      doc.text('Documento de remisión — no es factura de venta', pageW / 2, pageH - 8, { align: 'center' })
      doc.text(`Generado por TraceLog — tracelog.co  |  ${fmtDateTime()}`, pageW / 2, pageH - 4, { align: 'center' })
      // Page number
      const pageNum = (doc as unknown as { internal: { getNumberOfPages: () => number } }).internal.getNumberOfPages()
      const currentPage = (doc as unknown as { internal: { getCurrentPageInfo: () => { pageNumber: number } } }).internal.getCurrentPageInfo().pageNumber
      if (pageNum > 1) {
        doc.text(`Página ${currentPage} de ${pageNum}`, pageW - margin, pageH - 4, { align: 'right' })
      }
    },
  })

  // Get Y after table
  y = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 6

  // ── 5. TOTALS BOX ──────────────────────────────────────────────────
  const totBoxW = 80
  const totBoxX = pageW - margin - totBoxW
  const totRows: [string, string, boolean?][] = [
    ['Subtotal', fmtMoney(data.subtotal)],
  ]
  if (data.total_discount > 0) totRows.push(['Descuento', `- ${fmtMoney(data.total_discount)}`])
  if (data.total_tax > 0) totRows.push(['IVA', fmtMoney(data.total_tax)])
  totRows.push(['TOTAL', fmtMoney(data.grand_total), true])

  doc.setDrawColor(203, 213, 225)
  doc.setLineWidth(0.3)
  const totBoxH = totRows.length * 7 + 4
  doc.roundedRect(totBoxX, y, totBoxW, totBoxH, 2, 2, 'S')

  let ty = y + 6
  for (const [label, value, isBold] of totRows) {
    doc.setFontSize(isBold ? 10 : 8)
    doc.setFont('helvetica', isBold ? 'bold' : 'normal')
    doc.setTextColor(isBold ? 15 : 100, isBold ? 23 : 116, isBold ? 42 : 139)
    doc.text(label, totBoxX + 4, ty)
    doc.setTextColor(15, 23, 42)
    doc.text(value as string, totBoxX + totBoxW - 4, ty, { align: 'right' })
    ty += 7
  }

  // Items count on the left
  doc.setFontSize(8)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(100, 116, 139)
  doc.text(`${data.total_items} ítems — ${data.total_quantity} unidades`, margin, y + 6)

  y += totBoxH + 5

  // Notes
  if (data.notes) {
    doc.setFontSize(8)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(100, 116, 139)
    doc.text(`Notas: ${data.notes}`, margin, y)
    y += 8
  }

  // ── 6. SIGNATURES ──────────────────────────────────────────────────
  // Ensure signatures fit — if not enough space, add a new page
  if (y > pageH - 60) {
    doc.addPage()
    y = margin
  }

  y = Math.max(y + 10, pageH - 55)
  const sigW = (contentW - 20) / 2

  // Left: Dispatched by
  const sigLeftX = margin
  doc.setDrawColor(100, 116, 139)
  doc.setLineWidth(0.3)
  doc.line(sigLeftX, y, sigLeftX + sigW, y)
  doc.setFontSize(9)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('Despachado por', sigLeftX, y + 5)
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(8)
  doc.setTextColor(100, 116, 139)
  doc.text('Nombre: _______________', sigLeftX, y + 12)
  doc.text('Cédula: _______________', sigLeftX, y + 18)
  doc.text('Fecha:  _______________', sigLeftX, y + 24)

  // Right: Received by
  const sigRightX = pageW - margin - sigW
  doc.line(sigRightX, y, sigRightX + sigW, y)
  doc.setFontSize(9)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('Recibido por', sigRightX, y + 5)
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(8)
  doc.setTextColor(100, 116, 139)
  doc.text('Nombre: _______________', sigRightX, y + 12)
  doc.text('Cédula: _______________', sigRightX, y + 18)
  doc.text('Fecha:  _______________', sigRightX, y + 24)
  doc.text('Firma:  _______________', sigRightX, y + 30)

  // ── 7. FOOTER (already handled in didDrawPage) ────────────────────

  // Save
  const customerNit = data.customer.nit || 'SIN-NIT'
  doc.save(`REM-${data.remission_number}-${customerNit}.pdf`)
}
