import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import QRCode from 'qrcode'
import { drawLogo } from './pdfLogo'

/**
 * Genera un PDF autocontenido de trazabilidad de una carga/lote.
 *
 * Diseñado para exportación a mercados que NO requieren EUDR (USA, resto del
 * mundo) — por eso no depende del módulo de compliance ni de tener un registro
 * EUDR creado. Los datos vienen del `/api/v1/assets/:id` + `/api/v1/assets/:id/events`,
 * que están disponibles siempre que el módulo Logística esté activo.
 *
 * Contenido:
 *   1. Header con logo + número de reporte + fecha de emisión.
 *   2. Ficha de la carga: producto, cantidad, estado actual, custodio actual,
 *      organización origen, metadata técnica.
 *   3. Anclaje blockchain: mint address cNFT, Merkle tree, tx firma, link a
 *      Solscan, QR pointing a la URL pública /verificar/...
 *   4. Cadena de custodia: tabla cronológica de eventos con tipo, fechas,
 *      from/to wallet, hash, tx sig (si anclado), ubicación.
 *   5. Footer con leyenda de cómo verificar los hashes y la URL pública.
 */

export interface TraceabilityAsset {
  id: string
  asset_mint: string
  product_type: string
  metadata: Record<string, unknown>
  current_custodian_wallet: string
  state: string
  last_event_hash: string | null
  blockchain_asset_id: string | null
  blockchain_tree_address: string | null
  blockchain_tx_signature: string | null
  blockchain_status: string
  is_compressed: boolean
  created_at: string
  updated_at: string
}

export interface TraceabilityEvent {
  id: string
  event_type: string
  from_wallet: string | null
  to_wallet: string | null
  timestamp: string
  location?: { lat?: number; lng?: number; city?: string; country?: string; label?: string } | null
  data?: Record<string, unknown>
  prev_event_hash: string | null
  event_hash: string
  solana_tx_sig: string | null
  anchored: boolean
  notes?: string | null
}

export interface TraceabilityPDFInput {
  asset: TraceabilityAsset
  events: TraceabilityEvent[]
  organization?: { name: string; description?: string | null } | null
  publicVerifyUrl: string        // ej: https://trace.app/verificar/CACAO-NS-2026-001
  solanaCluster?: 'devnet' | 'mainnet-beta'
  generatedAt?: Date
}

/* ── Helpers ──────────────────────────────────────────────────────────────── */

function fmtDateTime(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '--'
  return d.toLocaleString('es-CO', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function fmtNow(): string {
  return new Date().toLocaleString('es-CO', {
    day: '2-digit', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function shortHash(h: string | null | undefined, chars = 8): string {
  if (!h) return '--'
  return h.length <= chars * 2 + 3 ? h : `${h.slice(0, chars)}…${h.slice(-chars)}`
}

function explorerTx(sig: string, cluster: string): string {
  return `https://solscan.io/tx/${sig}?cluster=${cluster}`
}

function explorerAddr(addr: string, cluster: string): string {
  return `https://solscan.io/account/${addr}?cluster=${cluster}`
}

function eventTypeLabel(t: string): string {
  const map: Record<string, string> = {
    CREATED: 'Creación (Mint)',
    HANDOFF: 'Entrega (Handoff)',
    ARRIVED: 'Llegada',
    LOADED: 'Cargado',
    QC_PASSED: 'QC Aprobado',
    QC_FAILED: 'QC Rechazado',
    RELEASED: 'Liberado',
    BURN: 'Destrucción',
  }
  return map[t.toUpperCase()] ?? t
}

function reportNumber(asset: TraceabilityAsset, when: Date): string {
  const short = asset.id.slice(0, 8).toUpperCase()
  const yyyymmdd = when.toISOString().slice(0, 10).replace(/-/g, '')
  return `TRZ-${yyyymmdd}-${short}`
}

/* ── Main ─────────────────────────────────────────────────────────────────── */

export async function generateTraceabilityPDF(input: TraceabilityPDFInput): Promise<void> {
  const { asset, events, organization, publicVerifyUrl } = input
  const cluster = input.solanaCluster ?? 'devnet'
  const when = input.generatedAt ?? new Date()

  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const pageW = doc.internal.pageSize.getWidth()
  const pageH = doc.internal.pageSize.getHeight()
  const margin = 15
  const contentW = pageW - margin * 2

  const reportNum = reportNumber(asset, when)
  const cargoName = String(asset.metadata?.name ?? asset.metadata?.cargoName ?? asset.product_type ?? 'Carga')
  const quantity = asset.metadata?.quantity ?? asset.metadata?.peso_kg ?? asset.metadata?.weight ?? '--'
  const unit = asset.metadata?.unit ?? asset.metadata?.unidad ?? 'u'
  const origin = String(asset.metadata?.origin ?? asset.metadata?.origen ?? '--')
  const grade = String(asset.metadata?.grade ?? asset.metadata?.calidad ?? asset.metadata?.quality ?? '--')

  let y = margin

  /* ── 1. HEADER ──────────────────────────────────────────────────────────── */
  drawLogo(doc, margin, y + 1, 14)

  doc.setFontSize(16)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('TraceLog', margin + 18, y + 7)

  doc.setFontSize(10)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(100, 116, 139)
  doc.text('Reporte de Trazabilidad', margin + 18, y + 12)

  // Right: report metadata box
  const boxW = 72
  const boxX = pageW - margin - boxW
  const boxH = 26
  doc.setDrawColor(203, 213, 225)
  doc.setLineWidth(0.5)
  doc.roundedRect(boxX, y, boxW, boxH, 2, 2, 'S')

  doc.setFontSize(10)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('N° DE REPORTE', boxX + boxW / 2, y + 6, { align: 'center' })

  doc.setFontSize(12)
  doc.setTextColor(37, 99, 235)
  doc.text(reportNum, boxX + boxW / 2, y + 13, { align: 'center' })

  doc.setFontSize(8)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(100, 116, 139)
  doc.text(`Emitido: ${fmtNow()}`, boxX + boxW / 2, y + 19, { align: 'center' })
  doc.text(`Red: Solana ${cluster}`, boxX + boxW / 2, y + 23, { align: 'center' })

  y += Math.max(boxH, 20) + 6

  /* ── 2. CARGO SHEET ────────────────────────────────────────────────────── */
  doc.setDrawColor(203, 213, 225)
  doc.setLineWidth(0.3)
  const cargoH = 46
  doc.roundedRect(margin, y, contentW, cargoH, 2, 2, 'S')

  doc.setFontSize(11)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('FICHA DE LA CARGA', margin + 4, y + 6)

  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  const leftX = margin + 4
  const rightX = margin + contentW / 2 + 4
  let ly = y + 12
  const addRow = (lbl: string, val: string, x: number) => {
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(71, 85, 105)
    doc.text(lbl, x, ly)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(15, 23, 42)
    doc.text(val, x + 32, ly)
  }

  addRow('Carga:', cargoName, leftX); ly += 5
  addRow('Producto:', asset.product_type || '--', leftX); ly += 5
  addRow('Cantidad:', `${quantity} ${unit}`, leftX); ly += 5
  addRow('Origen:', origin, leftX); ly += 5
  addRow('Calidad:', grade, leftX); ly += 5

  ly = y + 12
  addRow('Estado:', asset.state || '--', rightX); ly += 5
  addRow('Organización:', organization?.name ?? '--', rightX); ly += 5
  addRow('Custodio actual:', shortHash(asset.current_custodian_wallet, 8), rightX); ly += 5
  addRow('Creado:', fmtDateTime(asset.created_at), rightX); ly += 5
  addRow('Última actualización:', fmtDateTime(asset.updated_at), rightX); ly += 5

  y += cargoH + 6

  /* ── 3. BLOCKCHAIN ANCHORING + QR ──────────────────────────────────────── */
  const bchH = 52
  doc.roundedRect(margin, y, contentW, bchH, 2, 2, 'S')

  doc.setFontSize(11)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('ANCLAJE EN BLOCKCHAIN (Solana)', margin + 4, y + 6)

  // QR on the right
  const qrSize = 32
  const qrX = pageW - margin - qrSize - 2
  const qrY = y + 8
  try {
    const qrDataUrl = await QRCode.toDataURL(publicVerifyUrl, { width: 300, margin: 1 })
    doc.addImage(qrDataUrl, 'PNG', qrX, qrY, qrSize, qrSize)
  } catch {
    // fallback: draw a placeholder rect
    doc.setFillColor(241, 245, 249)
    doc.rect(qrX, qrY, qrSize, qrSize, 'F')
    doc.setFontSize(7)
    doc.setTextColor(100, 116, 139)
    doc.text('QR no\ndisponible', qrX + qrSize / 2, qrY + qrSize / 2, { align: 'center' })
  }

  doc.setFontSize(7)
  doc.setTextColor(100, 116, 139)
  doc.text('Verificación pública', qrX + qrSize / 2, qrY + qrSize + 3, { align: 'center' })

  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  ly = y + 12
  const addBch = (lbl: string, val: string) => {
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(71, 85, 105)
    doc.text(lbl, leftX, ly)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(15, 23, 42)
    doc.text(val, leftX + 40, ly)
  }

  addBch('Mint cNFT:', shortHash(asset.asset_mint, 10)); ly += 5
  addBch('Merkle tree:', shortHash(asset.blockchain_tree_address, 10)); ly += 5
  addBch('Tx firma (mint):', shortHash(asset.blockchain_tx_signature, 10)); ly += 5
  addBch('Estado:', asset.blockchain_status); ly += 5
  addBch('Último hash:', shortHash(asset.last_event_hash, 10)); ly += 5
  addBch('Compressed:', asset.is_compressed ? 'Sí (cNFT)' : 'No'); ly += 5

  // Clickable links below
  if (asset.asset_mint) {
    doc.setFontSize(8)
    doc.setTextColor(37, 99, 235)
    const linkY = y + bchH - 3
    doc.textWithLink('Ver cNFT en Solscan →', leftX, linkY, { url: explorerAddr(asset.asset_mint, cluster) })
    if (asset.blockchain_tx_signature) {
      doc.textWithLink('Ver tx mint →', leftX + 48, linkY, { url: explorerTx(asset.blockchain_tx_signature, cluster) })
    }
    doc.textWithLink('Verificación pública →', leftX + 80, linkY, { url: publicVerifyUrl })
  }

  y += bchH + 6

  /* ── 4. CUSTODY CHAIN TABLE ────────────────────────────────────────────── */
  doc.setFontSize(11)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('CADENA DE CUSTODIA', margin, y + 4)

  doc.setFontSize(8)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(100, 116, 139)
  doc.text(`${events.length} eventos. Cada hash se calcula como SHA-256(evento + prev_hash). Alterar un evento rompe toda la cadena.`,
    margin, y + 8.5)

  y += 11

  const tableRows = events.map((e) => [
    fmtDateTime(e.timestamp),
    eventTypeLabel(e.event_type),
    shortHash(e.from_wallet, 6),
    shortHash(e.to_wallet, 6),
    e.location?.label ?? e.location?.city ?? '--',
    shortHash(e.event_hash, 6),
    e.anchored ? `✓ ${shortHash(e.solana_tx_sig, 6)}` : 'pendiente',
  ])

  autoTable(doc, {
    startY: y,
    head: [['Fecha', 'Evento', 'De', 'A', 'Ubicación', 'Hash', 'Tx Solana']],
    body: tableRows,
    theme: 'striped',
    styles: { fontSize: 7, cellPadding: 1.5, textColor: [15, 23, 42] },
    headStyles: { fillColor: [37, 99, 235], textColor: [255, 255, 255], fontSize: 7.5, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    columnStyles: {
      0: { cellWidth: 24 },
      1: { cellWidth: 26 },
      2: { cellWidth: 22 },
      3: { cellWidth: 22 },
      4: { cellWidth: 28 },
      5: { cellWidth: 22, font: 'courier' },
      6: { cellWidth: 'auto', font: 'courier' },
    },
    didDrawPage: (data) => {
      // Footer on every page
      const footY = pageH - 10
      doc.setDrawColor(226, 232, 240)
      doc.setLineWidth(0.3)
      doc.line(margin, footY - 2, pageW - margin, footY - 2)
      doc.setFontSize(7)
      doc.setFont('helvetica', 'normal')
      doc.setTextColor(100, 116, 139)
      doc.text('TraceLog — Reporte generado automáticamente, firmado criptográficamente en Solana.', margin, footY + 2)
      doc.text(`Página ${data.pageNumber}`, pageW - margin, footY + 2, { align: 'right' })
    },
  })

  // Move below table
  // @ts-expect-error lastAutoTable is injected by autotable
  const finalY: number = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 8

  /* ── 5. VERIFICATION INSTRUCTIONS ─────────────────────────────────────── */
  let vy = finalY
  if (vy > pageH - 40) {
    doc.addPage()
    vy = margin
  }

  doc.setFillColor(240, 253, 244)
  doc.setDrawColor(187, 247, 208)
  doc.roundedRect(margin, vy, contentW, 30, 2, 2, 'FD')

  doc.setFontSize(10)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(22, 101, 52)
  doc.text('Cómo verificar este reporte independientemente', margin + 4, vy + 6)

  doc.setFontSize(8)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(22, 101, 52)
  const lines = [
    '1. Escanear el código QR de este documento — no requiere cuenta ni login.',
    '2. Para cada evento de la cadena, abrir el link a Solscan y confirmar que la firma del custodio es válida.',
    '3. Recalcular localmente SHA-256(JSON canónico del evento + prev_hash) y comparar con la columna "Hash".',
    'La plataforma Trace paga los fees de Solana; los custodios firman con sus llaves privadas registradas.',
  ]
  let vly = vy + 11
  for (const ln of lines) {
    doc.text(ln, margin + 4, vly)
    vly += 4
  }

  /* ── SAVE ─────────────────────────────────────────────────────────────── */
  doc.save(`${reportNum}.pdf`)
}
