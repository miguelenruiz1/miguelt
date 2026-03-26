import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, Shield, CheckCircle2, Clock, Package, MapPin, Calendar, ExternalLink, AlertTriangle } from 'lucide-react'
import { usePublicBatchVerification } from '@/hooks/useInventory'

const STATUS_BADGES: Record<string, { color: string; label: string }> = {
  ok: { color: 'bg-green-100 text-green-700', label: 'Vigente' },
  expiring_soon: { color: 'bg-amber-100 text-amber-700', label: 'Pronto a vencer' },
  expired: { color: 'bg-red-100 text-red-700', label: 'Vencido' },
  no_expiry: { color: 'bg-gray-100 text-gray-600', label: 'Sin vencimiento' },
}

export default function PublicVerifyPage() {
  const [searchParams] = useSearchParams()
  const initialBatch = searchParams.get('batch') || ''
  const tenantId = searchParams.get('tenant') || 'default'

  const [batchInput, setBatchInput] = useState(initialBatch)
  const [searchBatch, setSearchBatch] = useState(initialBatch)

  const { data: verification, isLoading, error } = usePublicBatchVerification(searchBatch, tenantId)

  const handleSearch = () => {
    if (batchInput.trim()) setSearchBatch(batchInput.trim())
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-emerald-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-3xl mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 bg-indigo-600 rounded-xl flex items-center justify-center">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Trace</h1>
              <p className="text-xs text-gray-500">Verificacion de trazabilidad blockchain</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8">
        {/* Search */}
        <div className="bg-white rounded-2xl shadow-sm border p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Verificar Lote</h2>
          <p className="text-sm text-gray-500 mb-4">Ingrese el numero de lote o escanee el codigo QR del producto</p>
          <div className="flex gap-2">
            <input
              value={batchInput}
              onChange={e => setBatchInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="LOT-CAFE-2026-Q1-001"
              className="flex-1 border rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
            <button onClick={handleSearch} disabled={isLoading} className="px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 inline-flex items-center gap-2 font-medium">
              <Search className="h-4 w-4" /> Verificar
            </button>
          </div>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="text-center py-12">
            <div className="h-8 w-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-gray-500">Consultando blockchain...</p>
          </div>
        )}

        {/* Error */}
        {error && searchBatch && !isLoading && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-2" />
            <p className="text-red-700 font-medium">Lote no encontrado</p>
            <p className="text-sm text-red-500 mt-1">El numero de lote "{searchBatch}" no existe en el sistema</p>
          </div>
        )}

        {/* Result */}
        {verification && !isLoading && (
          <div className="space-y-6">
            {/* Product info */}
            <div className="bg-white rounded-2xl shadow-sm border p-6">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Package className="h-5 w-5 text-indigo-600" />
                    <h3 className="text-lg font-bold text-gray-900">{verification.product_name}</h3>
                  </div>
                  <p className="text-sm text-gray-500">SKU: {verification.product_sku}</p>
                </div>
                {verification.blockchain_status !== 'none' && (
                  <span className="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-medium inline-flex items-center gap-1">
                    <Shield className="h-3 w-3" /> Blockchain
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 mt-6">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Lote</p>
                  <p className="font-mono font-medium text-gray-900">{verification.batch_number}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Estado</p>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGES[verification.expiration_status]?.color || 'bg-gray-100'}`}>
                    {STATUS_BADGES[verification.expiration_status]?.label || verification.expiration_status}
                  </span>
                </div>
                {verification.manufacture_date && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Calendar className="h-3 w-3" /> Fabricacion</p>
                    <p className="text-sm text-gray-900">{verification.manufacture_date}</p>
                  </div>
                )}
                {verification.expiration_date && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Calendar className="h-3 w-3" /> Vencimiento</p>
                    <p className="text-sm text-gray-900">{verification.expiration_date}</p>
                  </div>
                )}
                {verification.origin_supplier && (
                  <div className="col-span-2">
                    <p className="text-xs text-gray-500 mb-1 flex items-center gap-1"><MapPin className="h-3 w-3" /> Origen</p>
                    <p className="text-sm text-gray-900">{verification.origin_supplier}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Proof chain */}
            {verification.proof_chain.length > 0 && (
              <div className="bg-white rounded-2xl shadow-sm border p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900">Cadena de Trazabilidad</h3>
                  <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
                    {verification.total_events_anchored} eventos en blockchain
                  </span>
                </div>
                <div className="space-y-0">
                  {verification.proof_chain.map((entry, i) => (
                    <div key={i} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className={`h-8 w-8 rounded-full flex items-center justify-center ${entry.anchor_tx_sig ? 'bg-emerald-100' : 'bg-gray-100'}`}>
                          {entry.anchor_tx_sig ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                          ) : (
                            <Clock className="h-4 w-4 text-gray-400" />
                          )}
                        </div>
                        {i < verification.proof_chain.length - 1 && (
                          <div className="w-0.5 h-8 bg-gray-200" />
                        )}
                      </div>
                      <div className="pb-6">
                        <p className="text-sm font-medium text-gray-900">{entry.description}</p>
                        {entry.timestamp && (
                          <p className="text-xs text-gray-500 mt-0.5">{new Date(entry.timestamp).toLocaleString()}</p>
                        )}
                        {entry.solana_explorer_url && (
                          <a href={entry.solana_explorer_url} target="_blank" rel="noopener noreferrer" className="text-xs text-indigo-600 hover:underline mt-1 inline-flex items-center gap-1">
                            <ExternalLink className="h-3 w-3" /> Ver en Solana Explorer
                          </a>
                        )}
                        {entry.anchor_hash && (
                          <p className="text-[10px] font-mono text-gray-400 mt-1 break-all">hash: {entry.anchor_hash}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Verification footer */}
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
              <CheckCircle2 className="h-6 w-6 text-emerald-600 mx-auto mb-2" />
              <p className="text-sm font-medium text-emerald-800">Verificacion completada</p>
              <p className="text-xs text-emerald-600 mt-1">
                Consultado: {new Date(verification.verified_at).toLocaleString()}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t bg-white mt-12">
        <div className="max-w-3xl mx-auto px-4 py-4 text-center">
          <p className="text-xs text-gray-400">Powered by Trace — Trazabilidad blockchain en Solana</p>
        </div>
      </div>
    </div>
  )
}
