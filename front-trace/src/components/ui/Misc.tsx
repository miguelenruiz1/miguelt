/** Spinner, Card, EmptyState, HashChip — small utility components */
import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { cn, copyToClipboard, shortHash } from '@/lib/utils'

// ─── Spinner ──────────────────────────────────────────────────────────────────

export function Spinner({ className }: { className?: string }) {
  return (
    <svg className={cn('animate-spin h-5 w-5 text-indigo-600', className)} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 100 16v-4l-3 3 3 3v-4a8 8 0 01-8-8z" />
    </svg>
  )
}

// ─── Card ─────────────────────────────────────────────────────────────────────

interface CardProps { className?: string; children: React.ReactNode }

export function Card({ className, children }: CardProps) {
  return (
    <div className={cn('rounded-xl border border-gray-200 bg-white shadow-sm p-6', className)}>
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
      {icon && <div className="text-gray-300 mb-1">{icon}</div>}
      <p className="text-sm font-medium text-gray-600">{title}</p>
      {description && <p className="text-xs text-gray-400 max-w-xs">{description}</p>}
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
        'font-mono text-xs text-gray-500 hover:text-gray-800',
        'bg-gray-100 hover:bg-gray-200 border border-gray-200 transition-colors cursor-pointer',
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
  return <div className={cn('animate-pulse rounded-lg bg-gray-200', className)} />
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
  default: 'border-gray-200',
  success: 'border-emerald-200',
  warning: 'border-amber-200',
  danger: 'border-red-200',
}

const statIconBg = {
  default: 'bg-gray-100 text-gray-600 shadow-inner',
  success: 'bg-emerald-100 text-emerald-700 shadow-inner',
  warning: 'bg-amber-100 text-amber-700 shadow-inner',
  danger: 'bg-red-100 text-red-700 shadow-inner',
}

export function StatCard({ label, value, icon, variant = 'default', sub }: StatCardProps) {
  return (
    <div className={cn('rounded-xl border border-gray-200 bg-white shadow-sm py-6 px-7 transition-all', statBorder[variant])}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
          {sub && <p className="mt-1 text-xs font-medium text-gray-400">{sub}</p>}
        </div>
        <div className={cn('flex h-11 w-11 items-center justify-center rounded-full shrink-0', statIconBg[variant])}>
          {icon}
        </div>
      </div>
    </div>
  )
}
