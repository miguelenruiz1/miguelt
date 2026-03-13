import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { AlertTriangle, Info, Trash2 } from 'lucide-react'
import { useConfirmStore, type ConfirmVariant } from '@/store/confirm'
import { cn } from '@/lib/utils'

const variantConfig: Record<ConfirmVariant, {
  icon: React.ReactNode
  iconBg: string
  accentColor: string
  buttonClass: string
}> = {
  danger: {
    icon: <Trash2 className="h-5 w-5 text-red-600" />,
    iconBg: 'bg-red-50',
    accentColor: 'from-red-500 to-rose-500',
    buttonClass: 'bg-red-600 hover:bg-red-700 text-white',
  },
  warning: {
    icon: <AlertTriangle className="h-5 w-5 text-amber-600" />,
    iconBg: 'bg-amber-50',
    accentColor: 'from-amber-500 to-orange-500',
    buttonClass: 'bg-amber-600 hover:bg-amber-700 text-white',
  },
  info: {
    icon: <Info className="h-5 w-5 text-indigo-600" />,
    iconBg: 'bg-indigo-50',
    accentColor: 'from-indigo-500 to-violet-500',
    buttonClass: 'bg-indigo-600 hover:bg-indigo-700 text-white',
  },
}

export function ConfirmDialog() {
  const { open, title, message, variant, confirmLabel, cancelLabel, accept, cancel } =
    useConfirmStore()

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') cancel()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, cancel])

  if (!open) return null

  const config = variantConfig[variant]

  return createPortal(
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      aria-describedby="confirm-message"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-gray-900/50 animate-fade-in"
        onClick={cancel}
      />

      {/* Panel */}
      <div className={cn(
        'relative w-full max-w-sm rounded-xl bg-white border border-gray-200 shadow-xl',
        'animate-slide-up overflow-hidden',
      )}>
        {/* Accent stripe */}
        <div className={cn('h-0.5 bg-gradient-to-r', config.accentColor)} />

        {/* Content */}
        <div className="px-6 pt-5 pb-4 text-center">
          <div className={cn(
            'mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full',
            config.iconBg,
          )}>
            {config.icon}
          </div>
          <h3 id="confirm-title" className="text-sm font-semibold text-gray-900">
            {title}
          </h3>
          <p id="confirm-message" className="mt-1.5 text-xs text-gray-500 leading-relaxed">
            {message}
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-2.5 px-6 pb-5">
          <button
            onClick={cancel}
            className="flex-1 rounded-xl border border-gray-200 px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={accept}
            className={cn(
              'flex-1 rounded-lg px-4 py-2 text-xs font-semibold transition-colors shadow-sm',
              config.buttonClass,
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
