import { useState } from 'react'

export function CopyableId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false)

  return (
    <span
      className="font-mono text-[10px] text-muted-foreground cursor-pointer hover:text-primary transition-colors"
      title={copied ? '¡Copiado!' : id}
      onClick={(e) => {
        e.stopPropagation()
        e.preventDefault()
        navigator.clipboard.writeText(id)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      }}
    >
      {copied ? '✓ copiado' : `${id.slice(0, 8)}…`}
    </span>
  )
}
