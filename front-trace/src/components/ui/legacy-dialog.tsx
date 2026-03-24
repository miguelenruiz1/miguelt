/**
 * Legacy Dialog wrapper — provides the old Dialog API on top of shadcn Dialog.
 *
 * Old API: <Dialog open={} onClose={} title="" description="" size="" footer={}>
 * New API: shadcn <Dialog> + <DialogContent> + <DialogHeader> etc.
 *
 * This bridge lets all existing modals work without rewriting them.
 */
import { type ReactNode } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'

interface LegacyDialogProps {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg'
  footer?: ReactNode
}

const sizes = {
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-lg',
  lg: 'sm:max-w-2xl',
}

export function LegacyDialog({
  open,
  onClose,
  title,
  description,
  children,
  size = 'md',
  footer,
}: LegacyDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className={sizes[size]}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <div className="py-2">{children}</div>
        {footer && <DialogFooter>{footer}</DialogFooter>}
      </DialogContent>
    </Dialog>
  )
}
