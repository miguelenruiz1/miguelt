import { useState } from 'react'
import { KeyRound, Eye, EyeOff, Check } from 'lucide-react'
import { useAdminStore } from '@/store/admin'
import { Button } from '@/components/ui/Button'
import { Dialog } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'

interface TopbarProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
}

export function Topbar({ title, subtitle, actions }: TopbarProps) {
  const [open, setOpen] = useState(false)
  const [showKey, setShowKey] = useState(false)
  const [draft, setDraft] = useState('')
  const { adminKey, setAdminKey } = useAdminStore()

  const handleSave = () => {
    setAdminKey(draft.trim())
    setOpen(false)
    setDraft('')
  }

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between gap-3 min-h-[4rem] px-4 sm:px-6 bg-white border-b border-gray-200 shrink-0 shadow-sm -mx-4 -mt-4 md:-mx-6 md:-mt-6 mb-4 md:mb-6">
      <div className="min-w-0">
        <h1 className="text-lg sm:text-xl font-bold text-gray-900 tracking-tight truncate">{title}</h1>
        {subtitle && <p className="text-xs sm:text-sm font-medium text-gray-500 mt-0.5 truncate">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-2 sm:gap-4 shrink-0">
        {actions}
        <Button
          variant={adminKey ? 'ghost' : 'outline'}
          size="sm"
          className="rounded-xl font-semibold shadow-sm transition-all hover:shadow-md"
          onClick={() => { setDraft(adminKey); setOpen(true) }}
          title="Configurar clave admin para operaciones de liberación"
        >
          <KeyRound className="h-4 w-4 mr-1.5" />
          {adminKey
            ? <span className="text-emerald-600 flex items-center gap-1"><Check className="h-3.5 w-3.5" /> Clave activa</span>
            : 'Clave Admin'}
        </Button>
      </div>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Clave Admin"
        description="Requerida para operaciones de LIBERACIÓN. Se almacena en localStorage."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={handleSave}>Guardar</Button>
          </>
        }
      >
        <div className="relative">
          <Input
            label="TRACE_ADMIN_KEY"
            type={showKey ? 'text' : 'password'}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ingresa clave admin..."
            hint="Debe coincidir con TRACE_ADMIN_KEY en el .env del backend"
          />
          <button
            type="button"
            className="absolute right-3 top-[34px] text-gray-400 hover:text-gray-700 transition-colors"
            onClick={() => setShowKey((s) => !s)}
          >
            {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </Dialog>
    </header>
  )
}
