import { cn } from "@/lib/utils"

/**
 * Base skeleton primitive. Renders an animated placeholder bar.
 *
 * Accepts all <div> props for backward-compatibility with the shadcn-style
 * `<Skeleton className="h-4 w-24" />` call site. Optionally pass `rows` to
 * render a vertical stack of lines.
 */
function Skeleton({
  className,
  rows,
  ...props
}: React.ComponentProps<"div"> & { rows?: number }) {
  if (rows && rows > 1) {
    return (
      <div
        data-slot="skeleton"
        className={cn("animate-pulse space-y-2", className)}
        {...props}
      >
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-4 bg-muted rounded-md" />
        ))}
      </div>
    )
  }
  return (
    <div
      data-slot="skeleton"
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  )
}

/**
 * Table skeleton with a header row and N body rows of M columns.
 * Use while initial data is loading (before data arrives).
 */
function SkeletonTable({
  columns = 5,
  rows = 6,
  className,
}: {
  columns?: number
  rows?: number
  className?: string
}) {
  return (
    <div
      data-slot="skeleton-table"
      className={cn(
        "animate-pulse overflow-hidden rounded-lg border border-border bg-card",
        className,
      )}
    >
      <div className="flex gap-3 border-b border-border bg-muted/40 px-4 py-3">
        {Array.from({ length: columns }).map((_, i) => (
          <div
            key={`h-${i}`}
            className="h-3 flex-1 rounded bg-muted"
            style={{ maxWidth: i === 0 ? "40%" : undefined }}
          />
        ))}
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={`r-${r}`} className="flex gap-3 px-4 py-4">
            {Array.from({ length: columns }).map((_, c) => (
              <div
                key={`c-${r}-${c}`}
                className="h-4 flex-1 rounded bg-muted/70"
                style={{ maxWidth: c === 0 ? "40%" : undefined }}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Card-shaped skeleton (for detail panels and summary cards).
 */
function SkeletonCard({
  lines = 3,
  className,
}: {
  lines?: number
  className?: string
}) {
  return (
    <div
      data-slot="skeleton-card"
      className={cn(
        "animate-pulse rounded-lg border border-border bg-card p-4 space-y-3",
        className,
      )}
    >
      <div className="h-5 w-1/3 rounded bg-muted" />
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="h-3 rounded bg-muted/70"
            style={{ width: `${100 - i * 10}%` }}
          />
        ))}
      </div>
    </div>
  )
}

/**
 * Grid of skeleton cards — useful for dashboards with KPI tiles.
 */
function SkeletonGrid({
  items = 4,
  columns = 4,
  className,
}: {
  items?: number
  columns?: number
  className?: string
}) {
  const colsClass =
    columns === 2
      ? "md:grid-cols-2"
      : columns === 3
        ? "md:grid-cols-3"
        : "md:grid-cols-4"
  return (
    <div className={cn("grid grid-cols-1 gap-4", colsClass, className)}>
      {Array.from({ length: items }).map((_, i) => (
        <SkeletonCard key={i} lines={2} />
      ))}
    </div>
  )
}

export { Skeleton, SkeletonTable, SkeletonCard, SkeletonGrid }
