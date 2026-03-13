/**
 * Generates a printable traceability certificate for a cargo's chain of custody.
 * Opens a styled HTML document in a new window ready for Print → Save as PDF.
 */
import type { Asset, CustodyEvent } from '@/types/api'
import type { SolanaCluster } from '@/store/settings'

const EVENT_LABELS: Record<string, string> = {
  CREATED: 'Registrado',
  HANDOFF: 'Transferencia',
  ARRIVED: 'Llegada',
  LOADED: 'Cargado',
  QC: 'Control de Calidad',
  RELEASED: 'Liberado',
  BURN: 'Entrega Completada',
}

const STATE_LABELS: Record<string, string> = {
  in_custody: 'En Custodia',
  in_transit: 'En Tránsito',
  loaded: 'Cargado',
  qc_passed: 'QC Aprobado',
  qc_failed: 'QC Rechazado',
  released: 'Liberado',
  burned: 'Completado',
}

function explorerTxUrl(sig: string, cluster: SolanaCluster) {
  return `https://explorer.solana.com/tx/${sig}?cluster=${cluster}`
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('es-CO', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function shortKey(key: string) {
  if (key.length <= 12) return key
  return `${key.slice(0, 6)}...${key.slice(-4)}`
}

export function generateTraceabilityCertificate(
  asset: Asset,
  events: CustodyEvent[],
  cluster: SolanaCluster,
) {
  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  )

  const meta = asset.metadata as Record<string, unknown>
  const cargoName = (meta?.name as string) || asset.product_type
  const isSimulated = asset.asset_mint.startsWith('sim') || asset.asset_mint.startsWith('SIM_')
  const allAnchored = sorted.every((e) => e.anchored)

  const eventsHtml = sorted.map((e, i) => {
    const isSimSig = e.solana_tx_sig?.startsWith('SIM_') || e.solana_tx_sig?.startsWith('sim')
    const txLink = e.solana_tx_sig && !isSimSig
      ? `<a href="${explorerTxUrl(e.solana_tx_sig, cluster)}" target="_blank" style="color:#059669;text-decoration:none;font-family:monospace;font-size:11px;">Verificar en Solana ↗</a>`
      : e.solana_tx_sig
        ? `<span style="color:#94a3b8;font-family:monospace;font-size:11px;">Simulado</span>`
        : `<span style="color:#f59e0b;font-size:11px;">Pendiente de certificación</span>`

    const location = e.location?.label ? `<br/><span style="color:#64748b;">Ubicación: ${e.location.label}</span>` : ''
    const notes = e.data?.notes ? `<br/><span style="color:#64748b;">Notas: ${e.data.notes}</span>` : ''
    const qcResult = e.event_type === 'QC' && e.data?.result
      ? `<br/><span style="color:${e.data.result === 'pass' ? '#059669' : '#dc2626'};font-weight:600;">Resultado: ${e.data.result === 'pass' ? 'Aprobado' : 'Rechazado'}</span>`
      : ''

    return `
      <tr style="border-bottom:1px solid #e2e8f0;">
        <td style="padding:10px 8px;text-align:center;font-weight:600;color:#475569;">${i + 1}</td>
        <td style="padding:10px 8px;font-size:12px;white-space:nowrap;">${fmtDate(e.timestamp)}</td>
        <td style="padding:10px 8px;">
          <strong>${EVENT_LABELS[e.event_type] ?? e.event_type}</strong>
          ${location}${notes}${qcResult}
        </td>
        <td style="padding:10px 8px;font-family:monospace;font-size:11px;word-break:break-all;">${e.from_wallet ? shortKey(e.from_wallet) : '—'}</td>
        <td style="padding:10px 8px;font-family:monospace;font-size:11px;word-break:break-all;">${e.to_wallet ? shortKey(e.to_wallet) : '—'}</td>
        <td style="padding:10px 8px;font-family:monospace;font-size:10px;word-break:break-all;color:#64748b;">${e.event_hash.slice(0, 16)}...</td>
        <td style="padding:10px 8px;">${txLink}</td>
      </tr>
    `
  }).join('')

  const metaRows = [
    meta?.weight && `<tr><td style="padding:4px 0;color:#64748b;">Peso</td><td style="padding:4px 0;font-weight:600;">${meta.weight} ${meta.weight_unit ?? 'kg'}</td></tr>`,
    meta?.quality_grade && `<tr><td style="padding:4px 0;color:#64748b;">Calidad</td><td style="padding:4px 0;font-weight:600;">${meta.quality_grade}</td></tr>`,
    meta?.origin && `<tr><td style="padding:4px 0;color:#64748b;">Origen</td><td style="padding:4px 0;font-weight:600;">${meta.origin}</td></tr>`,
    meta?.description && `<tr><td style="padding:4px 0;color:#64748b;">Descripción</td><td style="padding:4px 0;">${meta.description}</td></tr>`,
  ].filter(Boolean).join('')

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <title>Certificado de Trazabilidad — ${cargoName}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; padding: 40px; font-size: 13px; line-height: 1.5; }
    @media print {
      body { padding: 20px; }
      .no-print { display: none !important; }
      table { page-break-inside: auto; }
      tr { page-break-inside: avoid; }
    }
    h1 { font-size: 22px; color: #1e293b; }
    h2 { font-size: 15px; color: #334155; margin: 24px 0 12px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; padding: 8px; background: #f8fafc; border-bottom: 2px solid #cbd5e1; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 30px; border-bottom: 3px solid #4f46e5; padding-bottom: 20px; }
    .logo { font-size: 28px; font-weight: 800; color: #4f46e5; }
    .logo span { color: #94a3b8; font-weight: 400; font-size: 14px; display: block; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
    .badge-ok { background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }
    .badge-pending { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0; }
    .info-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; }
    .info-box label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; display: block; margin-bottom: 4px; }
    .info-box p { font-size: 13px; font-weight: 600; color: #1e293b; word-break: break-all; }
    .hash-chain { background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 16px 0; }
    .hash-chain p { font-family: monospace; font-size: 11px; color: #475569; word-break: break-all; }
    .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e2e8f0; text-align: center; color: #94a3b8; font-size: 11px; }
    .print-btn { position: fixed; top: 20px; right: 20px; padding: 10px 24px; background: #4f46e5; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 14px; box-shadow: 0 2px 8px rgba(79,70,229,0.3); }
    .print-btn:hover { background: #4338ca; }
  </style>
</head>
<body>
  <button class="print-btn no-print" onclick="window.print()">Imprimir / Guardar PDF</button>

  <div class="header">
    <div>
      <div class="logo">TraceLog <span>Certificado de Trazabilidad Inmutable</span></div>
    </div>
    <div style="text-align:right;">
      <span class="badge ${allAnchored ? 'badge-ok' : 'badge-pending'}">${allAnchored ? 'Completamente Certificado' : 'Certificación en Progreso'}</span>
      <p style="font-size:11px;color:#94a3b8;margin-top:6px;">Generado: ${fmtDate(new Date().toISOString())}</p>
    </div>
  </div>

  <h2>Información de la Carga</h2>
  <div class="info-grid">
    <div class="info-box">
      <label>Nombre</label>
      <p>${cargoName}</p>
    </div>
    <div class="info-box">
      <label>Tipo de Producto</label>
      <p>${asset.product_type}</p>
    </div>
    <div class="info-box">
      <label>Estado Actual</label>
      <p>${STATE_LABELS[asset.state] ?? asset.state}</p>
    </div>
    <div class="info-box">
      <label>Custodio Actual</label>
      <p style="font-family:monospace;font-size:11px;">${asset.current_custodian_wallet}</p>
    </div>
    <div class="info-box">
      <label>Identificador Blockchain</label>
      <p style="font-family:monospace;font-size:11px;">${isSimulated ? 'Modo simulación' : asset.asset_mint}</p>
    </div>
    <div class="info-box">
      <label>Fecha de Registro</label>
      <p>${fmtDate(asset.created_at)}</p>
    </div>
  </div>

  ${metaRows ? `
  <h2>Metadatos de la Carga</h2>
  <table style="max-width:400px;">
    ${metaRows}
  </table>
  ` : ''}

  <h2>Cadena de Custodia (${sorted.length} eventos)</h2>
  <p style="color:#64748b;margin-bottom:12px;font-size:12px;">
    Cada evento está vinculado criptográficamente al anterior mediante hash SHA-256 y certificado en la blockchain de Solana (${cluster}).
    Los enlaces "Verificar en Solana" permiten comprobar de forma independiente cada registro.
  </p>
  <table>
    <thead>
      <tr>
        <th style="width:30px;">#</th>
        <th>Fecha</th>
        <th>Evento</th>
        <th>De</th>
        <th>A</th>
        <th>Hash</th>
        <th>Blockchain</th>
      </tr>
    </thead>
    <tbody>
      ${eventsHtml}
    </tbody>
  </table>

  <div class="hash-chain">
    <strong style="font-size:12px;color:#334155;">Cadena de Hashes Criptográfica</strong>
    <p style="margin-top:8px;">Último hash: ${asset.last_event_hash ?? '—'}</p>
    <p style="margin-top:4px;font-size:10px;color:#94a3b8;">
      Cada evento contiene el hash del evento anterior, formando una cadena inmutable verificable.
      Cualquier alteración de un evento invalida todos los hashes posteriores.
    </p>
  </div>

  <div class="footer">
    <p><strong>TraceLog</strong> — Sistema de Trazabilidad con Cadena de Custodia Inmutable</p>
    <p style="margin-top:4px;">Este certificado fue generado automáticamente. La autenticidad de cada evento puede verificarse de forma independiente en la blockchain de Solana.</p>
    <p style="margin-top:4px;">Red: ${cluster} | ID: ${asset.id}</p>
  </div>
</body>
</html>`

  const w = window.open('', '_blank')
  if (w) {
    w.document.write(html)
    w.document.close()
  }
}
