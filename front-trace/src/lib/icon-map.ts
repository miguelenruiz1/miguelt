/**
 * Maps icon name strings (stored in DB) to Lucide React components.
 * Used by workflow-driven UI components.
 */
import type { LucideIcon } from 'lucide-react'
import {
  Package, Truck, MapPin, CheckCircle, CheckCircle2, XCircle,
  ShieldAlert, AlertTriangle, Lock, Unlock, Flame,
  PlusCircle, ArrowRight, Container, ClipboardCheck,
  PackageCheck, LogIn, LogOut, PlaneTakeoff, ShieldCheck,
  Thermometer, Search, Layers, MessageSquare, Undo2,
  Circle, Warehouse, Zap,
} from 'lucide-react'

const ICON_MAP: Record<string, LucideIcon> = {
  // State icons
  'package': Package,
  'truck': Truck,
  'map-pin': MapPin,
  'container': Container,
  'check-circle': CheckCircle,
  'check-circle-2': CheckCircle2,
  'x-circle': XCircle,
  'shield-alert': ShieldAlert,
  'alert-triangle': AlertTriangle,
  'lock': Lock,
  'unlock': Unlock,
  'flame': Flame,
  'warehouse': Warehouse,
  'undo-2': Undo2,
  'zap': Zap,

  // Event type icons
  'plus-circle': PlusCircle,
  'arrow-right': ArrowRight,
  'clipboard-check': ClipboardCheck,
  'package-check': PackageCheck,
  'log-in': LogIn,
  'log-out': LogOut,
  'plane-takeoff': PlaneTakeoff,
  'shield-check': ShieldCheck,
  'thermometer': Thermometer,
  'search': Search,
  'layers': Layers,
  'message-square': MessageSquare,
  'circle': Circle,
}

export function resolveIcon(name: string | null | undefined): LucideIcon {
  if (!name) return Circle
  return ICON_MAP[name] ?? Circle
}

/**
 * Convert a hex color to a CSS-friendly className approach.
 * Returns inline style for dynamic workflow colors.
 */
export function colorStyle(hex: string) {
  return {
    color: hex,
    backgroundColor: `${hex}15`,
    borderColor: `${hex}30`,
  }
}
