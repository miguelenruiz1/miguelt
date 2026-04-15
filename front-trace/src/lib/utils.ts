import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ─── Formatting helpers ──────────────────────────────────────────────────────

export function shortPubkey(key: string, chars = 6): string {
  if (!key || key.length <= chars * 2 + 3) return key
  return `${key.slice(0, chars)}...${key.slice(-chars)}`
}

export function shortHash(hash: string, chars = 8): string {
  if (!hash) return ''
  return hash.length <= chars ? hash : hash.slice(0, chars) + '…'
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-CO', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function fmtDateShort(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-CO', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

/** Format a number for display in es-CO locale (1.000.000 instead of 1,000,000). */
export function fmtNumber(
  value: number | string | null | undefined,
  opts: Intl.NumberFormatOptions = {},
): string {
  if (value === null || value === undefined || value === '') return '—'
  const num = typeof value === 'string' ? Number(value) : value
  if (!Number.isFinite(num)) return '—'
  return num.toLocaleString('es-CO', opts)
}

/** Format a money amount. Default currency COP → "$1.000.000". */
export function fmtMoney(
  value: number | string | null | undefined,
  currency: string = 'COP',
): string {
  if (value === null || value === undefined || value === '') return '—'
  const num = typeof value === 'string' ? Number(value) : value
  if (!Number.isFinite(num)) return '—'
  // For COP we drop decimals by default (whole pesos); for others, keep 2.
  const fractionDigits = currency === 'COP' ? 0 : 2
  try {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency,
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    }).format(num)
  } catch {
    return `$${num.toLocaleString('es-CO')} ${currency}`
  }
}

export function newUUID(): string {
  return crypto.randomUUID()
}

export function parseTags(input: string): string[] {
  return input.split(',').map(t => t.trim()).filter(Boolean)
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

export function tryParseJson(str: string): unknown | null {
  try {
    return JSON.parse(str)
  } catch {
    return null
  }
}
