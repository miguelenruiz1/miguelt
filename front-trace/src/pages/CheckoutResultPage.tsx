import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { CheckCircle2, XCircle, ArrowRight, Loader2, AlertTriangle } from 'lucide-react'

type TxStatus = 'loading' | 'approved' | 'declined' | 'pending' | 'error' | 'missing'

async function fetchWompiStatus(id: string): Promise<string | null> {
  // Public Wompi endpoint — try production first, fall back to sandbox.
  for (const base of ['https://production.wompi.co/v1', 'https://sandbox.wompi.co/v1']) {
    try {
      const r = await fetch(`${base}/transactions/${id}`)
      if (r.ok) {
        const body = await r.json()
        return body?.data?.status ?? null
      }
    } catch {
      // try next env
    }
  }
  return null
}

export function CheckoutResultPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const ref = searchParams.get('ref') ?? ''
  const id = searchParams.get('id') ?? ''

  const [status, setStatus] = useState<TxStatus>(() => (id ? 'loading' : 'missing'))

  useEffect(() => {
    if (!id) return
    let cancelled = false
    fetchWompiStatus(id).then(wompiStatus => {
      if (cancelled) return
      if (wompiStatus === 'APPROVED') setStatus('approved')
      else if (wompiStatus === 'DECLINED' || wompiStatus === 'VOIDED' || wompiStatus === 'ERROR') setStatus('declined')
      else if (wompiStatus === 'PENDING') setStatus('pending')
      else setStatus('error')
    })
    return () => { cancelled = true }
  }, [id])

  const copy = STATUS_COPY[status]

  return (
    <div className="flex items-center justify-center min-h-[60vh] p-6">
      <div className="w-full max-w-md rounded-3xl bg-card shadow-2xl p-10 text-center space-y-6">
        <div className="flex justify-center">
          <div className={`flex h-20 w-20 items-center justify-center rounded-full ${copy.iconBg} ring-4 ${copy.iconRing}`}>
            {copy.icon}
          </div>
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">{copy.title}</h1>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{copy.body}</p>
        </div>
        {(ref || id) && (
          <div className="rounded-2xl bg-muted border border-border px-4 py-3 text-xs text-muted-foreground space-y-1">
            {ref && <p>Referencia: <span className="font-mono font-semibold text-foreground">{ref}</span></p>}
            {id && <p>Transacción: <span className="font-mono font-semibold text-foreground">{id}</span></p>}
          </div>
        )}
        <button
          onClick={() => navigate(status === 'declined' || status === 'error' ? '/checkout' : '/marketplace')}
          className={`w-full rounded-2xl py-3 text-sm font-bold transition-colors flex items-center justify-center gap-2 ${
            status === 'approved'
              ? 'bg-primary text-white hover:bg-primary/90'
              : 'border border-border text-muted-foreground hover:bg-muted'
          }`}
        >
          {copy.cta} <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

const STATUS_COPY: Record<TxStatus, { title: string; body: string; cta: string; icon: JSX.Element; iconBg: string; iconRing: string }> = {
  loading: {
    title: 'Verificando tu pago',
    body: 'Estamos confirmando la transacción con Wompi. Esto toma unos segundos.',
    cta: 'Volver al Marketplace',
    icon: <Loader2 className="h-10 w-10 text-amber-500 animate-spin" />,
    iconBg: 'bg-amber-50',
    iconRing: 'ring-amber-100',
  },
  approved: {
    title: 'Pago aprobado',
    body: 'Wompi confirmó tu pago. Tu suscripción fue activada.',
    cta: 'Ir al Marketplace',
    icon: <CheckCircle2 className="h-10 w-10 text-emerald-500" />,
    iconBg: 'bg-emerald-50',
    iconRing: 'ring-emerald-100',
  },
  pending: {
    title: 'Pago pendiente',
    body: 'Wompi aún está procesando la transacción. Te notificaremos cuando se confirme.',
    cta: 'Volver al Marketplace',
    icon: <Loader2 className="h-10 w-10 text-amber-500 animate-spin" />,
    iconBg: 'bg-amber-50',
    iconRing: 'ring-amber-100',
  },
  declined: {
    title: 'Pago rechazado',
    body: 'Wompi rechazó la transacción. Podés reintentar con otro método de pago.',
    cta: 'Reintentar pago',
    icon: <XCircle className="h-10 w-10 text-red-500" />,
    iconBg: 'bg-red-50',
    iconRing: 'ring-red-100',
  },
  error: {
    title: 'No pudimos verificar el pago',
    body: 'No logramos confirmar el estado con Wompi. Revisá tu correo o volvé a intentar en unos minutos.',
    cta: 'Reintentar',
    icon: <AlertTriangle className="h-10 w-10 text-amber-500" />,
    iconBg: 'bg-amber-50',
    iconRing: 'ring-amber-100',
  },
  missing: {
    title: 'Procesando pago',
    body: 'Estamos esperando la confirmación de Wompi. Si ya completaste el pago, tu suscripción se activará en unos minutos.',
    cta: 'Volver al Marketplace',
    icon: <Loader2 className="h-10 w-10 text-amber-500 animate-spin" />,
    iconBg: 'bg-amber-50',
    iconRing: 'ring-amber-100',
  },
}
