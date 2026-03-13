import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow } from 'date-fns'

/** Merge Tailwind classes safely */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Generate a browser-native UUID (used for Idempotency-Key) */
export function newUUID(): string {
  return crypto.randomUUID()
}

/** Truncate a hash/pubkey: show first 8 + last 4 chars */
export function shortHash(hash: string, head = 8, tail = 4): string {
  if (hash.length <= head + tail + 2) return hash
  return `${hash.slice(0, head)}…${hash.slice(-tail)}`
}

/** Short pubkey */
export function shortPubkey(pk: string): string {
  if (pk.length <= 16) return pk
  return `${pk.slice(0, 8)}…${pk.slice(-6)}`
}

/** Copy to clipboard — returns promise */
export async function copyToClipboard(text: string): Promise<void> {
  await navigator.clipboard.writeText(text)
}

/** Format ISO date as readable */
export function fmtDate(iso: string): string {
  return format(new Date(iso), 'MMM d, yyyy  HH:mm')
}

/** Relative time ("3 minutes ago") */
export function fmtRelative(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true })
}

/** Format ISO date short */
export function fmtDateShort(iso: string): string {
  return format(new Date(iso), 'dd/MM/yy HH:mm')
}

/** Parse comma-separated tags from a string */
export function parseTags(raw: string): string[] {
  return raw
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)
}

/** Try parse JSON string, return object or null */
export function tryParseJson(s: string): Record<string, unknown> | null {
  try { return JSON.parse(s) as Record<string, unknown> }
  catch { return null }
}
