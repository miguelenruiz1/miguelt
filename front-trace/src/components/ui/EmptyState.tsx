import * as React from "react"
import { Link } from "react-router-dom"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

export interface EmptyStateAction {
  label: string
  onClick?: () => void
  to?: string
  icon?: React.ElementType
}

export interface EmptyStateProps {
  icon: React.ElementType
  title: string
  description: string
  action?: EmptyStateAction
  secondaryAction?: EmptyStateAction
  illustration?: React.ReactNode
  className?: string
  compact?: boolean
}

/**
 * Reusable empty-state block. Use when a list/collection has loaded and is
 * empty — NOT while data is still loading.
 *
 * Usage:
 * ```tsx
 * <EmptyState
 *   icon={Package}
 *   title="Aún no tenés productos"
 *   description="Creá tu primer producto del catálogo"
 *   action={{ label: "Nuevo producto", to: "/inventario/productos/nuevo" }}
 * />
 * ```
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  illustration,
  className,
  compact = false,
}: EmptyStateProps) {
  return (
    <div
      data-slot="empty-state"
      className={cn(
        "flex flex-col items-center justify-center text-center",
        compact ? "py-10 px-6" : "py-16 px-8",
        className,
      )}
    >
      {illustration ? (
        <div className="mb-4">{illustration}</div>
      ) : (
        <div
          className={cn(
            "mb-4 inline-flex items-center justify-center rounded-full bg-muted/60 text-muted-foreground",
            compact ? "h-12 w-12" : "h-16 w-16",
          )}
        >
          <Icon className={compact ? "h-6 w-6" : "h-8 w-8"} aria-hidden />
        </div>
      )}
      <h3
        className={cn(
          "font-semibold text-foreground",
          compact ? "text-base" : "text-lg",
        )}
      >
        {title}
      </h3>
      <p className="mt-1.5 max-w-md text-sm text-muted-foreground">
        {description}
      </p>
      {(action || secondaryAction) && (
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          {action && <EmptyStateButton action={action} variant="default" />}
          {secondaryAction && (
            <EmptyStateButton action={secondaryAction} variant="outline" />
          )}
        </div>
      )}
    </div>
  )
}

function EmptyStateButton({
  action,
  variant,
}: {
  action: EmptyStateAction
  variant: "default" | "outline"
}) {
  const ActionIcon = action.icon
  const content = (
    <>
      {ActionIcon && <ActionIcon className="h-4 w-4" aria-hidden />}
      {action.label}
    </>
  )
  if (action.to) {
    return (
      <Link
        to={action.to}
        className={cn(
          "inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
          variant === "default"
            ? "bg-primary text-primary-foreground border-transparent hover:bg-primary/90"
            : "bg-transparent border-border text-foreground hover:bg-muted",
        )}
      >
        {content}
      </Link>
    )
  }
  return (
    <Button
      variant={variant}
      size="sm"
      className="gap-2"
      onClick={action.onClick}
      type="button"
    >
      {content}
    </Button>
  )
}

export default EmptyState
