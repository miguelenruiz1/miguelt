import { Shield, ExternalLink, CheckCircle2, Clock, XCircle, Loader2 } from 'lucide-react'
import { useBlockchainStatus, useBlockchainVerify } from '@/hooks/useInventory'
import { useToastStore } from '@/store/toast'

interface Props {
  entityType: 'purchase_order' | 'sales_order' | 'batch' | 'movement'
  entityId: string
}

const STATUS_CONFIG = {
  none: { icon: Shield, color: 'text-gray-400', bg: 'bg-gray-50', label: 'Sin anclar' },
  pending: { icon: Clock, color: 'text-amber-500', bg: 'bg-amber-50', label: 'Pendiente' },
  anchored: { icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-50', label: 'Anclado en Solana' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50', label: 'Error' },
}

export default function BlockchainPanel({ entityType, entityId }: Props) {
  const { data: status, isLoading } = useBlockchainStatus(entityType, entityId)
  const verifyMut = useBlockchainVerify()
  const toast = useToastStore()

  if (isLoading) {
    return (
      <div className="bg-gray-50 rounded-xl border p-4 flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" /> Cargando estado blockchain...
      </div>
    )
  }

  if (!status) return null

  const config = STATUS_CONFIG[status.anchor_status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.none
  const Icon = config.icon

  const handleVerify = async () => {
    try {
      const result = await verifyMut.mutateAsync({ entityType, entityId })
      if (result.is_anchored && result.solana_verified) {
        toast.success('Verificado en Solana: el registro es autentico e inmutable')
      } else if (result.is_anchored) {
        toast.success('Anclado en Solana (verificacion on-chain pendiente)')
      } else {
        toast.error('No se encontro el registro en blockchain')
      }
    } catch (e: any) {
      toast.error(e.message || 'Error al verificar')
    }
  }

  const explorerUrl = status.anchor_tx_sig
    ? status.anchor_tx_sig.startsWith('SIM_')
      ? `https://explorer.solana.com/tx/${status.anchor_tx_sig}?cluster=devnet`
      : `https://explorer.solana.com/tx/${status.anchor_tx_sig}`
    : null

  return (
    <div className={`${config.bg} rounded-xl border p-4`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Icon className={`h-5 w-5 ${config.color}`} />
          <div>
            <p className="text-sm font-medium text-gray-900">Blockchain</p>
            <p className={`text-xs ${config.color}`}>{config.label}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {status.anchor_status === 'anchored' && (
            <button onClick={handleVerify} disabled={verifyMut.isPending} className="text-xs text-indigo-600 hover:underline inline-flex items-center gap-1">
              {verifyMut.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Shield className="h-3 w-3" />}
              Verificar
            </button>
          )}
          {explorerUrl && (
            <a href={explorerUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-indigo-600 hover:underline inline-flex items-center gap-1">
              <ExternalLink className="h-3 w-3" /> Solana Explorer
            </a>
          )}
        </div>
      </div>

      {status.anchor_hash && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-xs text-gray-500">Hash SHA-256</p>
          <p className="text-xs font-mono text-gray-700 break-all mt-0.5">{status.anchor_hash}</p>
        </div>
      )}

      {status.anchor_tx_sig && (
        <div className="mt-2">
          <p className="text-xs text-gray-500">Solana TX</p>
          <p className="text-xs font-mono text-gray-700 break-all mt-0.5">{status.anchor_tx_sig}</p>
        </div>
      )}

      {status.anchored_at && (
        <div className="mt-2">
          <p className="text-xs text-gray-500">Anclado: {new Date(status.anchored_at).toLocaleString()}</p>
        </div>
      )}
    </div>
  )
}
