import * as React from "react"
import { AlertTriangle, RotateCcw, Mail } from "lucide-react"
import { Button } from "@/components/ui/Button"

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ReactNode | ((err: Error, reset: () => void) => React.ReactNode)
  onError?: (error: Error, info: React.ErrorInfo) => void
  onReset?: () => void
}

interface ErrorBoundaryState {
  error: Error | null
}

/**
 * Error boundary for React subtrees. Catches render/lifecycle errors and
 * shows a recoverable fallback. Wrap it around route outlets or risky
 * branches (lazy-loaded pages, third-party widgets, etc.).
 *
 * Does NOT catch: event handler errors, async errors, SSR errors.
 */
export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary] caught:", error, info)
    // Best-effort Sentry hook (if ever installed via window.Sentry)
    const w = window as unknown as {
      Sentry?: { captureException?: (e: unknown, ctx?: unknown) => void }
    }
    if (w.Sentry?.captureException) {
      try {
        w.Sentry.captureException(error, { extra: { componentStack: info.componentStack } })
      } catch {
        /* noop */
      }
    }
    this.props.onError?.(error, info)
  }

  reset = () => {
    this.setState({ error: null })
    this.props.onReset?.()
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    if (this.props.fallback) {
      if (typeof this.props.fallback === "function") {
        return this.props.fallback(error, this.reset)
      }
      return this.props.fallback
    }
    return <DefaultErrorFallback error={error} onReset={this.reset} />
  }
}

function DefaultErrorFallback({
  error,
  onReset,
}: {
  error: Error
  onReset: () => void
}) {
  const isDev = import.meta.env?.DEV
  const mailto = `mailto:soporte@trace.log?subject=${encodeURIComponent(
    "Error en la aplicación",
  )}&body=${encodeURIComponent(
    `Hola, encontré un error:\n\n${error.name}: ${error.message}\n\nURL: ${window.location.href}`,
  )}`

  return (
    <div
      role="alert"
      className="flex min-h-[60vh] items-center justify-center p-6"
    >
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 text-center shadow-sm">
        <div className="mx-auto mb-4 inline-flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertTriangle className="h-7 w-7" aria-hidden />
        </div>
        <h2 className="text-lg font-semibold text-foreground">
          Algo salió mal
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Ocurrió un error inesperado al cargar esta sección. Podés intentar
          recargar la página; si el problema persiste, avisanos.
        </p>
        {isDev && (
          <pre className="mt-4 max-h-40 overflow-auto rounded-md bg-muted p-3 text-left text-xs text-muted-foreground whitespace-pre-wrap">
            {error.name}: {error.message}
            {error.stack ? `\n\n${error.stack}` : ""}
          </pre>
        )}
        <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-center">
          <Button
            variant="default"
            size="sm"
            className="gap-2"
            onClick={() => {
              onReset()
              window.location.reload()
            }}
          >
            <RotateCcw className="h-4 w-4" aria-hidden />
            Recargar página
          </Button>
          <a
            href={mailto}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-transparent px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          >
            <Mail className="h-4 w-4" aria-hidden />
            Reportar el problema
          </a>
        </div>
      </div>
    </div>
  )
}

export default ErrorBoundary
