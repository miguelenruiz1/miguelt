import { createPortal } from 'react-dom'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import { useToastStore, type ToastVariant } from '@/store/toast'
import { cn } from '@/lib/utils'

const icons: Record<ToastVariant, React.ReactNode> = {
  success: <CheckCircle   className="h-4 w-4 text-emerald-600 shrink-0" />,
  error:   <AlertCircle   className="h-4 w-4 text-red-600     shrink-0" />,
  warning: <AlertTriangle className="h-4 w-4 text-amber-600   shrink-0" />,
  info:    <Info          className="h-4 w-4 text-indigo-600  shrink-0" />,
}

const variantStyles: Record<ToastVariant, string> = {
  success: 'border-l-4 border-l-emerald-500',
  error:   'border-l-4 border-l-red-500',
  warning: 'border-l-4 border-l-amber-500',
  info:    'border-l-4 border-l-indigo-500',
}

export function ToastContainer() {
  const { toasts, remove } = useToastStore()

  if (!toasts.length) return null

  return createPortal(
    <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            'pointer-events-auto flex items-center gap-3 rounded-lg px-4 py-3',
            'bg-white border border-gray-200 shadow-lg max-w-sm w-full animate-slide-up',
            variantStyles[t.variant],
          )}
        >
          {icons[t.variant]}
          <p className="flex-1 text-sm text-gray-800 font-medium">{t.message}</p>
          <button
            onClick={() => remove(t.id)}
            className="text-gray-400 hover:text-gray-600 transition-colors shrink-0"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>,
    document.body,
  )
}
