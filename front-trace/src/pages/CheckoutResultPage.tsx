import { useSearchParams, useNavigate } from 'react-router-dom'
import { CheckCircle2, XCircle, ArrowRight, Loader2 } from 'lucide-react'

export function CheckoutResultPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const ref = searchParams.get('ref') ?? ''
  const id = searchParams.get('id') ?? ''

  // Wompi appends ?id=<tx_id> to the redirect URL on completion
  // The ref format is "{tenant_id}:{invoice_id}"
  const hasTransaction = !!id

  return (
    <div className="flex items-center justify-center min-h-[60vh] p-6">
      <div className="w-full max-w-md rounded-3xl bg-white shadow-2xl p-10 text-center space-y-6">
        {hasTransaction ? (
          <>
            <div className="flex justify-center">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-emerald-50 ring-4 ring-emerald-100">
                <CheckCircle2 className="h-10 w-10 text-emerald-500" />
              </div>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Pago procesado</h1>
              <p className="mt-2 text-sm text-slate-500 leading-relaxed">
                Tu transaccion ha sido recibida. Wompi confirmara el pago y tu suscripcion se activara automaticamente.
              </p>
            </div>
            <div className="rounded-2xl bg-slate-50 border border-slate-200 px-4 py-3 text-xs text-slate-500 space-y-1">
              {ref && <p>Referencia: <span className="font-mono font-semibold text-slate-700">{ref}</span></p>}
              <p>Transaccion: <span className="font-mono font-semibold text-slate-700">{id}</span></p>
            </div>
            <button
              onClick={() => navigate('/marketplace')}
              className="w-full rounded-2xl bg-primary py-3 text-sm font-bold text-white hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
            >
              Ir al Marketplace <ArrowRight className="h-4 w-4" />
            </button>
          </>
        ) : (
          <>
            <div className="flex justify-center">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-amber-50 ring-4 ring-amber-100">
                <Loader2 className="h-10 w-10 text-amber-500 animate-spin" />
              </div>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Procesando pago</h1>
              <p className="mt-2 text-sm text-slate-500 leading-relaxed">
                Estamos esperando la confirmacion de Wompi. Si ya completaste el pago, tu suscripcion se activara en unos minutos.
              </p>
            </div>
            <button
              onClick={() => navigate('/marketplace')}
              className="w-full rounded-2xl border border-slate-200 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Volver al Marketplace
            </button>
          </>
        )}
      </div>
    </div>
  )
}
