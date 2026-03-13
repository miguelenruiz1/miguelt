import { create } from 'zustand'

export type ToastVariant = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  message: string
  variant: ToastVariant
}

interface ToastStore {
  toasts: Toast[]
  push: (message: string, variant?: ToastVariant) => void
  remove: (id: string) => void
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  push: (message, variant = 'info') => {
    const id = crypto.randomUUID()
    set((s) => ({ toasts: [...s.toasts, { id, message, variant }] }))
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 4000)
  },
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))

/** Convenience hook */
export function useToast() {
  const { push } = useToastStore()
  return {
    success: (msg: string) => push(msg, 'success'),
    error:   (msg: string) => push(msg, 'error'),
    warning: (msg: string) => push(msg, 'warning'),
    info:    (msg: string) => push(msg, 'info'),
  }
}
