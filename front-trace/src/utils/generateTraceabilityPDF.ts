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
  /**
   * Mapa pubkey → nombre legible. Si se provee, las columnas "De" y "A" del
   * PDF muestran el nombre real (ej. "Asocafé Huila") en lugar del hash
   * truncado.
   */
  walletNames?: Record<string, string>
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
    HANDOFF: 'Cambio de custodia',
    ARRIVED: 'Llegada a destino',
    LOADED: 'Cargada en vehículo',
    PICKUP: 'Recogida',
    DELIVERED: 'Entregada',
    DEPARTED: 'Salida',
    GATE_IN: 'Ingreso a terminal',
    GATE_OUT: 'Salida de terminal',
    SEALED: 'Sellada',
    UNSEALED: 'Desellada',
    QC: 'Inspección de calidad',
    QC_PASSED: 'QC aprobado',
    QC_FAILED: 'QC rechazado',
    INSPECTION: 'Inspección',
    TEMPERATURE_CHECK: 'Control de temperatura',
    DAMAGED: 'Daño reportado',
    CUSTOMS_HOLD: 'Retención aduanera',
    CUSTOMS_CLEARED: 'Aduana liberada',
    RELEASED: 'Liberada',
    BURN: 'Destrucción',
    RETURN: 'Devolución',
    CONSOLIDATED: 'Consolidada',
    DECONSOLIDATED: 'Desconsolidada',
    ANCHORED: 'Anclado en blockchain',
    NOTE: 'Nota interna',
    EVIDENCE: 'Evidencia adjunta',
  }
  // Manejar prefijo MOVE_TO_<STATE> que el backend genera para transiciones libres.
  const u = t.toUpperCase()
  const stripped = u.startsWith('MOVE_TO_') ? u.slice(8) : u
  return map[stripped] ?? stripped.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
}

function partyName(pubkey: string | null | undefined, walletNames?: Record<string, string>): string {
  if (!pubkey) return '—'
  const name = walletNames?.[pubkey]
  if (name && name.trim()) return name
  return shortHash(pubkey, 6)
}

function reportNumber(asset: TraceabilityAsset, when: Date): string {
  const short = asset.id.slice(0, 8).toUpperCase()
  const yyyymmdd = when.toISOString().slice(0, 10).replace(/-/g, '')
  return `TRZ-${yyyymmdd}-${short}`
}

/* ── Main ─────────────────────────────────────────────────────────────────── */

export async function generateTraceabilityPDF(input: TraceabilityPDFInput): Promise<void> {
  const { asset, events, organization, publicVerifyUrl, walletNames } = input
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
  addRow('Custodio actual:', partyName(asset.current_custodian_wallet, walletNames), rightX); ly += 5
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

  /* ── 4. NARRATIVA CRONOLÓGICA ───────────────────────────────────────────── */
  // Eventos ordenados ascendentes para narrar el recorrido como historia.
  const eventsAsc = [...events].sort(
    (a, b) => +new Date(a.timestamp) - +new Date(b.timestamp),
  )

  doc.setFontSize(11)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('RECORRIDO DE LA CARGA', margin, y + 4)

  doc.setFontSize(8)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(100, 116, 139)
  doc.text(
    'Resumen narrativo de los movimientos y eventos registrados, en orden cronológico.',
    margin, y + 8.5,
  )

  y += 12

  const narrativeText = (e: TraceabilityEvent): string => {
    const t = e.event_type.toUpperCase().replace(/^MOVE_TO_/, '')
    const from = partyName(e.from_wallet, walletNames)
    const to = partyName(e.to_wallet, walletNames)
    const place = e.location?.label || e.location?.city
    const placeStr = place ? ` en ${place}` : ''
    const note = e.notes ? ` — ${e.notes}` : ''
    switch (t) {
      case 'CREATED': return `${from} registró la carga en el sistema${placeStr}.${note}`
      case 'HANDOFF': return `${from} entregó la carga a ${to}${placeStr}.${note}`
      case 'PICKUP':  return `${to !== '—' ? to : from} recogió la carga${placeStr}.${note}`
      case 'LOADED':  return `${from} cargó la mercancía en el vehículo${placeStr}.${note}`
      case 'ARRIVED': return `La carga llegó a destino${placeStr} bajo custodia de ${from}.${note}`
      case 'DELIVERED': return `${from} entregó la carga al receptor final${placeStr}.${note}`
      case 'GATE_IN': return `Ingreso a terminal${placeStr} por ${from}.${note}`
      case 'GATE_OUT': return `Salida de terminal${placeStr} por ${from}.${note}`
      case 'SEALED': return `${from} selló la carga${placeStr}.${note}`
      case 'UNSEALED': return `${from} abrió el sello${placeStr}.${note}`
      case 'QC':
      case 'QC_PASSED': return `${from} realizó inspección de calidad y aprobó${placeStr}.${note}`
      case 'QC_FAILED': return `${from} realizó inspección y rechazó la carga${placeStr}.${note}`
      case 'INSPECTION': return `${from} inspeccionó la carga${placeStr}.${note}`
      case 'DAMAGED': return `Se reportó daño en la carga${placeStr} por ${from}.${note}`
      case 'CUSTOMS_HOLD': return `Aduana retuvo la carga${placeStr}.${note}`
      case 'CUSTOMS_CLEARED': return `Aduana liberó la carga${placeStr}.${note}`
      case 'TEMPERATURE_CHECK': return `Control de temperatura por ${from}${placeStr}.${note}`
      case 'RELEASED': return `${from} liberó la carga${placeStr}.${note}`
      case 'RETURN': return `Devolución de la carga${placeStr}.${note}`
      case 'BURN': return `Destrucción registrada${placeStr} por ${from}.${note}`
      case 'NOTE': return `Nota de ${from}${placeStr}: ${e.notes ?? '(sin texto)'}`
      case 'EVIDENCE': return `${from} adjuntó evidencia${placeStr}.${note}`
      case 'ANCHORED': return `Evento anclado en blockchain.`
      default: return `${eventTypeLabel(e.event_type)} por ${from}${placeStr}.${note}`
    }
  }

  doc.setFontSize(8.5)
  doc.setTextColor(15, 23, 42)
  for (let i = 0; i < eventsAsc.length; i++) {
    if (y > pageH - 25) { doc.addPage(); y = margin }
    const e = eventsAsc[i]
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(37, 99, 235)
    doc.text(`${i + 1}.`, margin, y)
    doc.setTextColor(71, 85, 105)
    doc.text(fmtDateTime(e.timestamp), margin + 6, y)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(15, 23, 42)
    const text = narrativeText(e)
    const wrapped = doc.splitTextToSize(text, contentW - 36)
    doc.text(wrapped, margin + 36, y)
    y += Math.max(5, wrapped.length * 4)
  }

  y += 4

  /* ── 5. TABLA TÉCNICA DE LA CADENA ──────────────────────────────────────── */
  if (y > pageH - 50) { doc.addPage(); y = margin }
  doc.setFontSize(11)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(15, 23, 42)
  doc.text('CADENA DE CUSTODIA — DETALLE TÉCNICO', margin, y + 4)

  doc.setFontSize(8)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(100, 116, 139)
  doc.text(`${events.length} eventos. Cada hash se calcula como SHA-256(evento + prev_hash). Alterar un evento rompe toda la cadena.`,
    margin, y + 8.5)

  y += 11

  const tableRows = events.map((e) => [
    fmtDateTime(e.timestamp),
    eventTypeLabel(e.event_type),
    partyName(e.from_wallet, walletNames),
    partyName(e.to_wallet, walletNames),
    e.location?.label ?? e.location?.city ?? '—',
    e.notes ?? '—',
    shortHash(e.event_hash, 6),
    e.anchored ? '✓ anclado' : 'pendiente',
  ])

  autoTable(doc, {
    startY: y,
    head: [['Fecha', 'Evento', 'De', 'A', 'Ubicación', 'Notas', 'Hash', 'Anclaje']],
    body: tableRows,
    theme: 'striped',
    styles: { fontSize: 7, cellPadding: 1.5, textColor: [15, 23, 42], overflow: 'linebreak' },
    headStyles: { fillColor: [37, 99, 235], textColor: [255, 255, 255], fontSize: 7.5, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    columnStyles: {
      0: { cellWidth: 22 },
      1: { cellWidth: 24 },
      2: { cellWidth: 26 },
      3: { cellWidth: 26 },
      4: { cellWidth: 22 },
      5: { cellWidth: 'auto' },
      6: { cellWidth: 18, font: 'courier' },
      7: { cellWidth: 16 },
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
    '2. Para cada evento, abrir el link a Solscan del cNFT y confirmar la firma del custodio.',
    '3. Recalcular SHA-256(JSON canónico del evento + prev_hash) y comparar con la columna "Hash".',
    'Los nombres mostrados ("Asocafé Huila", etc.) corresponden a wallets registradas en Trace; la',
    'pubkey real está siempre en blockchain. Trace paga los fees; los custodios firman con su llave.',
  ]
  let vly = vy + 11
  for (const ln of lines) {
    doc.text(ln, margin + 4, vly)
    vly += 4
  }

  /* ── SAVE ─────────────────────────────────────────────────────────────── */
  doc.save(`${reportNum}.pdf`)
}
