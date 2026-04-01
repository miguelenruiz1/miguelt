/** Spinner, Card, EmptyState, HashChip — small utility components */
import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { cn, copyToClipboard, shortHash } from '@/lib/utils'

// ─── Spinner ──────────────────────────────────────────────────────────────────

export function Spinner({ className }: { className?: string }) {
  return (
    <svg className={cn('animate-spin h-5 w-5 text-primary', className)} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 100 16v-4l-3 3 3 3v-4a8 8 0 01-8-8z" />
    </svg>
  )
}

// ─── Card ─────────────────────────────────────────────────────────────────────

interface CardProps { className?: string; children: React.ReactNode }

export function Card({ className, children }: CardProps) {
  return (
    <div className={cn('rounded-md border border-border bg-card  p-6', className)}>
      {children}
    </div>
  )
}

export function CardHeader({ className, children }: CardProps) {
  return <div className={cn('flex items-center justify-between mb-4', className)}>{children}</div>
}

// ─── EmptyState ───────────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center gap-3">
      {icon && <div className="text-muted-foreground/50 mb-1">{icon}</div>}
      <p className="text-sm font-medium text-foreground">{title}</p>
      {description && <p className="text-xs text-muted-foreground max-w-xs">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

// ─── HashChip ─────────────────────────────────────────────────────────────────

interface HashChipProps { hash: string; head?: number; tail?: number; className?: string }

export function HashChip({ hash, head = 8, tail = 4, className }: HashChipProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await copyToClipboard(hash)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <button
      onClick={handleCopy}
      title={hash}
      className={cn(
        'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5',
        'font-mono text-xs text-muted-foreground hover:text-foreground',
        'bg-muted hover:bg-muted/80 border border-border transition-colors cursor-pointer',
        className,
      )}
    >
      <span>{shortHash(hash, head, tail)}</span>
      {copied
        ? <Check className="h-3 w-3 text-emerald-500 shrink-0" />
        : <Copy className="h-3 w-3 shrink-0 opacity-50" />
      }
    </button>
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-primary/10', className)} />
}

// ─── StatCard ─────────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string
  value: string | number
  icon: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger'
  sub?: string
}

const statBorder = {
  default: 'border-border',
  success: 'border-emerald-500/20',
  warning: 'border-amber-500/20',
  danger: 'border-red-500/20',
}

const statIconBg = {
  default: 'bg-muted text-muted-foreground',
  success: 'bg-emerald-500/15 text-emerald-700',
  warning: 'bg-amber-500/15 text-amber-700',
  danger: 'bg-red-500/15 text-red-700',
}

export function StatCard({ label, value, icon, variant = 'default', sub }: StatCardProps) {
  return (
    <div className={cn('rounded-md border border-border bg-card  py-6 px-7 transition-all', statBorder[variant])}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-bold text-foreground">{value}</p>
          {sub && <p className="mt-1 text-xs font-medium text-muted-foreground">{sub}</p>}
        </div>
        <div className={cn('flex h-11 w-11 items-center justify-center rounded-full shrink-0', statIconBg[variant])}>
          {icon}
        </div>
      </div>
    </div>
  )
}
