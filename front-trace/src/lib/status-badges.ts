type Badge = { bg: string; text: string; label: string }

export const SUBSCRIPTION_STATUS_BADGE: Record<string, Badge> = {
  active:   { bg: 'bg-green-100', text: 'text-green-700', label: 'Activa' },
  trialing: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Prueba' },
  past_due: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Mora' },
  canceled: { bg: 'bg-red-100', text: 'text-red-700', label: 'Cancelada' },
  expired:  { bg: 'bg-secondary', text: 'text-muted-foreground', label: 'Expirada' },
}

