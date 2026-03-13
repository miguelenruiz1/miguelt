import { create } from 'zustand'

export type ConfirmVariant = 'danger' | 'warning' | 'info'

interface ConfirmState {
  open: boolean
  title: string
  message: string
  variant: ConfirmVariant
  confirmLabel: string
  cancelLabel: string
  resolve: ((value: boolean) => void) | null
}

interface ConfirmStore extends ConfirmState {
  show: (opts: {
    title?: string
    message: string
    variant?: ConfirmVariant
    confirmLabel?: string
    cancelLabel?: string
  }) => Promise<boolean>
  accept: () => void
  cancel: () => void
}

export const useConfirmStore = create<ConfirmStore>((set, get) => ({
  open: false,
  title: '',
  message: '',
  variant: 'danger',
  confirmLabel: 'Eliminar',
  cancelLabel: 'Cancelar',
  resolve: null,

  show: (opts) =>
    new Promise<boolean>((resolve) => {
      set({
        open: true,
        title: opts.title ?? 'Confirmar acción',
        message: opts.message,
        variant: opts.variant ?? 'danger',
        confirmLabel: opts.confirmLabel ?? 'Eliminar',
        cancelLabel: opts.cancelLabel ?? 'Cancelar',
        resolve,
      })
    }),

  accept: () => {
    get().resolve?.(true)
    set({ open: false, resolve: null })
  },

  cancel: () => {
    get().resolve?.(false)
    set({ open: false, resolve: null })
  },
}))

/** Convenience hook */
export function useConfirm() {
  const { show } = useConfirmStore()
  return show
}
