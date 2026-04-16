import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/lib/query-client'
import App from './App'
import './index.css'

// On initial page load, clear any stuck body styles from previous session
document.body.style.overflow = ''
document.body.style.pointerEvents = ''

// Global error telemetry. React ErrorBoundary only catches render/lifecycle
// errors — promise rejections from event handlers or useEffect bodies fall
// through to the host. Forward them to Sentry (when configured) and the
// console so they don't disappear silently in production.
type MaybeSentry = {
  Sentry?: {
    captureException?: (e: unknown, ctx?: unknown) => void
  }
}
const _reportAsync = (err: unknown, source: string) => {
  const s = (window as unknown as MaybeSentry).Sentry
  if (s?.captureException) {
    try { s.captureException(err, { tags: { source } }) } catch { /* noop */ }
  }
  // eslint-disable-next-line no-console
  console.error(`[${source}]`, err)
}
window.addEventListener('unhandledrejection', (e) => {
  _reportAsync(e.reason, 'unhandledrejection')
})
window.addEventListener('error', (e) => {
  _reportAsync(e.error ?? e.message, 'window.error')
})

// Patch React 19 removeChild crash — known issue with dynamic DOM reconciliation
// https://github.com/facebook/react/issues/29462
const origRemoveChild = Node.prototype.removeChild
// @ts-ignore
Node.prototype.removeChild = function <T extends Node>(child: T): T {
  if (child.parentNode !== this) {
    console.warn('React 19 removeChild patch: child is not a child of this node, skipping')
    return child
  }
  return origRemoveChild.call(this, child) as T
}

const origInsertBefore = Node.prototype.insertBefore
// @ts-ignore
Node.prototype.insertBefore = function <T extends Node>(newNode: T, refNode: Node | null): T {
  if (refNode && refNode.parentNode !== this) {
    console.warn('React 19 insertBefore patch: refNode is not a child of this node, skipping')
    return newNode
  }
  return origInsertBefore.call(this, newNode, refNode) as T
}

createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>,
)
