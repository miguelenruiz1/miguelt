import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  ShieldCheck, ShieldX, AlertTriangle, Download, ExternalLink,
  Loader2, Search, CheckCircle2, XCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useVerifyCertificate } from '@/hooks/useCompliance'

// ─── i18n strings ────────────────────────────────────────────────────────────

const i18n = {
  es: {
    verifying: 'Verificando certificado...',
    valid_title: 'CERTIFICADO VALIDO',
    revoked_title: 'CERTIFICADO REVOCADO',
    not_found_title: 'NO ENCONTRADO',
    not_found_desc: 'No se encontro un certificado con ese numero. Verifica e intenta de nuevo.',
    framework: 'Framework',
    commodity: 'Commodity',
    quantity: 'Cantidad',
    country: 'Pais de produccion',
    valid_from: 'Valido desde',
    valid_until: 'Valido hasta',
    deforestation_free: 'Libre de deforestacion',
    legal_compliance: 'Cumplimiento legal',
    plots: 'Parcelas verificadas',
    blockchain: 'Blockchain',
    cnft: 'cNFT Address',
    tx: 'Transaccion',
    download_pdf: 'Descargar PDF',
    generated_at: 'Generado el',
    yes: 'Si',
    no: 'No',
    placeholder: 'Ingresa el numero de certificado',
    verify_btn: 'Verificar',
    powered_by: 'Verificacion de trazabilidad por',
  },
  en: {
    verifying: 'Verifying certificate...',
    valid_title: 'VALID CERTIFICATE',
    revoked_title: 'REVOKED CERTIFICATE',
    not_found_title: 'NOT FOUND',
    not_found_desc: 'No certificate found with that number. Check and try again.',
    framework: 'Framework',
    commodity: 'Commodity',
    quantity: 'Quantity',
    country: 'Country of production',
    valid_from: 'Valid from',
    valid_until: 'Valid until',
    deforestation_free: 'Deforestation free',
    legal_compliance: 'Legal compliance',
    plots: 'Verified plots',
    blockchain: 'Blockchain',
    cnft: 'cNFT Address',
    tx: 'Transaction',
    download_pdf: 'Download PDF',
    generated_at: 'Generated on',
    yes: 'Yes',
    no: 'No',
    placeholder: 'Enter certificate number',
    verify_btn: 'Verify',
    powered_by: 'Traceability verification by',
  },
}

function getLang(): 'es' | 'en' {
  const nav = typeof navigator !== 'undefined' ? navigator.language : 'es'
  return nav.startsWith('es') ? 'es' : 'en'
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function VerifyCertificatePage() {
  const { certificateNumber = '' } = useParams<{ certificateNumber: string }>()
  const [manualNumber, setManualNumber] = useState('')
  const [activeNumber, setActiveNumber] = useState(certificateNumber)

  const { data, isLoading, isError } = useVerifyCertificate(activeNumber)
  const t = i18n[getLang()]

  function handleManualVerify(e: React.FormEvent) {
    e.preventDefault()
    if (manualNumber.trim()) {
      setActiveNumber(manualNumber.trim())
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-bold text-slate-900 tracking-tight">Trace</span>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 flex items-start justify-center px-4 py-10">
        <div className="w-full max-w-2xl">
          {/* Loading state */}
          {isLoading && activeNumber && (
            <div className="text-center py-16">
              <Loader2 className="h-10 w-10 text-primary mx-auto mb-4 animate-spin" />
              <p className="text-sm text-slate-500">{t.verifying}</p>
            </div>
          )}

          {/* Not found / Error */}
          {(isError || (data && !data.valid && data.status !== 'revoked')) && !isLoading && (
            <div className="text-center py-10">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-50 mx-auto mb-4">
                <AlertTriangle className="h-8 w-8 text-amber-500" />
              </div>
              <h1 className="text-xl font-bold text-amber-700 mb-2">{t.not_found_title}</h1>
              <p className="text-sm text-slate-500 max-w-sm mx-auto mb-8">{t.not_found_desc}</p>

              <form onSubmit={handleManualVerify} className="flex items-center gap-2 max-w-md mx-auto">
                <input value={manualNumber}
                  onChange={e => setManualNumber(e.target.value)}
                  placeholder={t.placeholder}
                  className="flex-1 rounded-lg border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono" />
                <button type="submit"
                  className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 transition-colors">
                  <Search className="h-4 w-4" /> {t.verify_btn}
                </button>
              </form>
            </div>
          )}

          {/* Valid certificate */}
          {data && data.valid && data.status === 'active' && !isLoading && (
            <div className="space-y-6">
              <div className="rounded-2xl bg-green-50 border border-green-200 p-6 text-center">
                <CheckCircle2 className="h-12 w-12 text-green-600 mx-auto mb-3" />
                <h1 className="text-xl font-bold text-green-800">{t.valid_title}</h1>
                <p className="text-sm font-mono text-green-700 mt-1">{data.certificate_number}</p>
              </div>

              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-100">
                <InfoRow label={t.framework} value={data.framework} />
                <InfoRow label={t.commodity} value={data.commodity_type} />
                <InfoRow label={t.quantity} value={data.quantity_kg != null ? `${Number(data.quantity_kg).toLocaleString()} kg` : null} />
                <InfoRow label={t.country} value={data.country_of_production} />
                <InfoRow label={t.valid_from} value={data.valid_from ? new Date(data.valid_from).toLocaleDateString() : null} />
                <InfoRow label={t.valid_until} value={data.valid_until ? new Date(data.valid_until).toLocaleDateString() : null} />
                <InfoRow label={t.deforestation_free}
                  value={data.deforestation_free != null ? (data.deforestation_free ? t.yes : t.no) : null}
                  valueColor={data.deforestation_free ? 'text-green-700' : 'text-red-600'} />
                <InfoRow label={t.legal_compliance}
                  value={data.legal_compliance != null ? (data.legal_compliance ? t.yes : t.no) : null}
                  valueColor={data.legal_compliance ? 'text-green-700' : 'text-red-600'} />
                <InfoRow label={t.plots} value={data.plots_count != null ? String(data.plots_count) : null} />
                {data.generated_at && (
                  <InfoRow label={t.generated_at} value={new Date(data.generated_at).toLocaleString()} />
                )}
              </div>

              {/* Blockchain */}
              {data.blockchain && (data.blockchain.cnft_address || data.blockchain.tx_signature) && (
                <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-2">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide">{t.blockchain}</h3>
                  {data.blockchain.cnft_address && (
                    <p className="text-xs text-slate-600">{t.cnft}: <code className="font-mono text-primary break-all">{data.blockchain.cnft_address}</code></p>
                  )}
                  {data.blockchain.tx_signature && (
                    <p className="text-xs text-slate-600">{t.tx}: <code className="font-mono text-primary break-all">{data.blockchain.tx_signature}</code></p>
                  )}
                </div>
              )}

              {/* PDF download */}
              {data.pdf_url && (
                <div className="text-center">
                  <a href={data.pdf_url} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors">
                    <Download className="h-4 w-4" /> {t.download_pdf}
                  </a>
                </div>
              )}
            </div>
          )}

          {/* Revoked certificate */}
          {data && data.status === 'revoked' && !isLoading && (
            <div className="space-y-6">
              <div className="rounded-2xl bg-red-50 border border-red-200 p-6 text-center">
                <ShieldX className="h-12 w-12 text-red-500 mx-auto mb-3" />
                <h1 className="text-xl font-bold text-red-800">{t.revoked_title}</h1>
                <p className="text-sm font-mono text-red-700 mt-1">{data.certificate_number}</p>
                {data.message && (
                  <p className="text-sm text-red-600 mt-2">{data.message}</p>
                )}
              </div>
            </div>
          )}

          {/* No number entered yet */}
          {!activeNumber && !isLoading && (
            <div className="text-center py-10">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 mx-auto mb-4">
                <Search className="h-8 w-8 text-slate-400" />
              </div>
              <h1 className="text-xl font-bold text-slate-700 mb-4">{t.verify_btn}</h1>
              <form onSubmit={handleManualVerify} className="flex items-center gap-2 max-w-md mx-auto">
                <input value={manualNumber}
                  onChange={e => setManualNumber(e.target.value)}
                  placeholder={t.placeholder}
                  className="flex-1 rounded-lg border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono" />
                <button type="submit"
                  className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary/90 transition-colors">
                  <Search className="h-4 w-4" /> {t.verify_btn}
                </button>
              </form>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white px-6 py-4 text-center">
        <p className="text-xs text-slate-400">
          {t.powered_by} <span className="font-semibold text-slate-600">Trace</span>
        </p>
      </footer>
    </div>
  )
}

function InfoRow({ label, value, valueColor }: { label: string; value: string | null; valueColor?: string }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between px-5 py-3.5">
      <span className="text-sm font-medium text-slate-500">{label}</span>
      <span className={cn('text-sm font-medium text-slate-900', valueColor)}>{value}</span>
    </div>
  )
}
