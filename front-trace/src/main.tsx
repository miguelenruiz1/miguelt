import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/lib/query-client'
import App from './App'
import './index.css'

// On initial page load, clear any stuck body styles from previous session
document.body.style.overflow = ''
document.body.style.pointerEvents = ''

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
