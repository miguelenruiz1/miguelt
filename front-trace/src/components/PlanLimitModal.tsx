import { AlertTriangle } from 'lucide-react'
import { LegacyDialog as Dialog } from '@/components/ui/legacy-dialog'
import { Button } from '@/components/ui/Button'
import { usePlanLimitStore } from '@/store/planLimit'

export function PlanLimitModal() {
  const { show, resource, current, limit, message, close } = usePlanLimitStore()

  // This modal is mounted as a global overlay outside RouterProvider (see
  // App.tsx), so useNavigate() throws "may be used only in the context of
  // a Router". window.location.href works without that context; the hard
  // reload is fine because the user is crossing into the billing flow
  // and we want a fresh query cache anyway.
  const handleViewPlans = () => {
    close()
    window.location.href = '/settings/billing'
  }

  return (
    <Dialog
      open={show}
      onClose={close}
      title={`Alcanzaste el limite de ${resource}`}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={close}>Cerrar</Button>
          <Button onClick={handleViewPlans}>Ver planes</Button>
        </>
      }
    >
      <div className="flex flex-col items-center text-center gap-4 py-2">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-amber-50">
          <AlertTriangle className="h-7 w-7 text-amber-500" />
        </div>

        <p className="text-sm text-muted-foreground">{message}</p>

        <div className="w-full rounded-xl border border-border bg-muted p-4">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-muted-foreground">Uso actual</span>
            <span className="font-semibold text-foreground">{current} / {limit}</span>
          </div>
          <div className="h-2.5 w-full rounded-full bg-gray-200 overflow-hidden">
            <div
              className="h-full rounded-full bg-red-500 transition-all"
              style={{ width: `${Math.min(100, (current / Math.max(limit, 1)) * 100)}%` }}
            />
          </div>
        </div>

        <p className="text-xs text-muted-foreground">
          Actualiza tu plan para obtener mas capacidad.
        </p>
      </div>
    </Dialog>
  )
}
