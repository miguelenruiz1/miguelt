/**
 * Toast bridge — delegates to sonner under the hood.
 * All existing code using useToast().success/error/etc. works unchanged.
 */
import { toast as sonner } from 'sonner'

export type ToastVariant = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  message: string
  variant: ToastVariant
}

// Keep the store interface for backward compatibility but delegate to sonner
export const useToastStore = {
  getState: () => ({ toasts: [] as Toast[], push: () => {}, remove: () => {} }),
}

/** Convenience hook — used by 50+ files */
export function useToast() {
  return {
    success: (msg: string) => sonner.success(msg),
    error:   (msg: string) => sonner.error(msg),
    warning: (msg: string) => sonner.warning(msg),
    info:    (msg: string) => sonner.info(msg),
  }
}
