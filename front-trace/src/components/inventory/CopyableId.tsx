import { useState } from 'react'

export function CopyableId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false)

  return (
    <span
      className="font-mono text-[10px] text-slate-400 cursor-pointer hover:text-indigo-600 transition-colors"
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
