import * as React from "react"
import { cn } from "@/lib/utils"

/* ── Input ────────────────────────────────────────────────────────────────── */

interface InputProps extends React.ComponentProps<"input"> {
  label?: string
  hint?: string
  error?: string
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, hint, error, ...props }, ref) => {
    return (
      <div>
        {label && (
          <label className="block text-sm font-medium text-foreground mb-1.5">
            {label}
          </label>
        )}
        <input
          type={type}
          ref={ref}
          className={cn(
            "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm  transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-destructive focus-visible:ring-destructive",
            className
          )}
          {...props}
        />
        {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
        {hint && !error && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </div>
    )
  }
)
Input.displayName = "Input"

/* ── Select ───────────────────────────────────────────────────────────────── */

interface SelectOption {
  label: string
  value: string
}

interface SelectProps extends Omit<React.ComponentProps<"select">, "children"> {
  label?: string
  hint?: string
  error?: string
  options?: SelectOption[]
  children?: React.ReactNode
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, hint, error, options, children, ...props }, ref) => {
    return (
      <div>
        {label && (
          <label className="block text-sm font-medium text-foreground mb-1.5">
            {label}
          </label>
        )}
        <select
          ref={ref}
          className={cn(
            "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm  transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-destructive focus-visible:ring-destructive",
            className
          )}
          {...props}
        >
          {options
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))
            : children}
        </select>
        {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
        {hint && !error && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </div>
    )
  }
)
Select.displayName = "Select"

/* ── Textarea ─────────────────────────────────────────────────────────────── */

interface TextareaProps extends React.ComponentProps<"textarea"> {
  label?: string
  hint?: string
  error?: string
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, hint, error, ...props }, ref) => {
    return (
      <div>
        {label && (
          <label className="block text-sm font-medium text-foreground mb-1.5">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={cn(
            "flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm  transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-destructive focus-visible:ring-destructive",
            className
          )}
          {...props}
        />
        {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
        {hint && !error && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </div>
    )
  }
)
Textarea.displayName = "Textarea"

export { Input, Select, Textarea }
