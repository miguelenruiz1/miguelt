import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from './Button'

interface DialogProps {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg'
  footer?: ReactNode
}

const sizes = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' }

export function Dialog({ open, onClose, title, description, children, size = 'md', footer }: DialogProps) {
  const overlayRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
      document.body.style.pointerEvents = ''
    }
    return () => {
      document.body.style.overflow = ''
      document.body.style.pointerEvents = ''
    }
  }, [open])

  if (!open) return null

  return createPortal(
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-gray-900/50 animate-fade-in"
        onClick={onClose}
      />

      {/* Panel */}
      <div className={cn(
        'relative w-full rounded-t-xl sm:rounded-xl bg-white border border-gray-200 shadow-xl',
        'flex flex-col max-h-[90dvh] animate-slide-up sm:max-w-[calc(100vw-2rem)]',
        sizes[size],
      )}>
        {/* Top accent stripe */}
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-indigo-600 rounded-t-sm" />

        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-6 pt-6 pb-4 border-b border-gray-200">
          <div>
            <h2 id="dialog-title" className="text-base font-semibold text-gray-900">
              {title}
            </h2>
            {description && (
              <p className="mt-0.5 text-sm text-gray-500">{description}</p>
            )}
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-sm">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.getElementById('portal-root') ?? document.body,
  )
}
