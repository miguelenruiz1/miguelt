interface TopbarProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
}

export function Topbar({ title, subtitle, actions }: TopbarProps) {
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between gap-3 min-h-[4rem] px-4 sm:px-6 bg-card border-b border-border shrink-0 -mx-4 -mt-4 md:-mx-6 md:-mt-6 mb-4 md:mb-6">
      <div className="min-w-0">
        <h1 className="text-lg sm:text-xl font-bold text-foreground tracking-tight truncate">{title}</h1>
        {subtitle && <p className="text-xs sm:text-sm font-medium text-muted-foreground mt-0.5 truncate">{subtitle}</p>}
      </div>

      {actions && (
        <div className="flex items-center gap-2 sm:gap-4 shrink-0">
          {actions}
        </div>
      )}
    </header>
  )
}
