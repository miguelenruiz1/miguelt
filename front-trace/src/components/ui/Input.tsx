import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const uid = id ?? label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={uid} className="mb-1 block text-sm font-medium text-gray-900">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={uid}
          className={cn(
            'w-full rounded-lg border border-gray-300 bg-transparent py-3 px-5 text-sm text-gray-900 outline-none',
            'placeholder:text-gray-400 transition',
            'focus:border-indigo-300 focus:ring-3 focus:ring-indigo-500/20',
            'disabled:cursor-default disabled:bg-gray-50',
            error && 'border-red-400 focus:border-red-500',
            className,
          )}
          {...props}
        />
        {error && <p className="text-xs text-red-600">{error}</p>}
        {hint && !error && <p className="text-xs text-gray-400">{hint}</p>}
      </div>
    )
  },
)
Input.displayName = 'Input'

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  hint?: string
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const uid = id ?? label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={uid} className="mb-1 block text-sm font-medium text-gray-900">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={uid}
          rows={3}
          className={cn(
            'w-full rounded-lg border border-gray-300 bg-transparent py-3 px-5 text-sm text-gray-900 outline-none',
            'placeholder:text-gray-400 transition resize-none',
            'focus:border-indigo-300 focus:ring-3 focus:ring-indigo-500/20',
            'disabled:cursor-default disabled:bg-gray-50',
            error && 'border-red-400',
            className,
          )}
          {...props}
        />
        {error && <p className="text-xs text-red-600">{error}</p>}
        {hint && !error && <p className="text-xs text-gray-400">{hint}</p>}
      </div>
    )
  },
)
Textarea.displayName = 'Textarea'

interface SelectProps extends InputHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options: { value: string; label: string }[]
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, options, id, value, onChange, ...props }, ref) => {
    const uid = id ?? label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={uid} className="mb-1 block text-sm font-medium text-gray-900">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={uid}
          value={value}
          onChange={onChange as React.ChangeEventHandler<HTMLSelectElement>}
          className={cn(
            'w-full rounded-lg border border-gray-300 bg-transparent py-3 px-5 text-sm text-gray-900 outline-none',
            'transition focus:border-indigo-300 focus:ring-3 focus:ring-indigo-500/20',
            'disabled:cursor-default disabled:bg-gray-50',
            error && 'border-red-400',
            className,
          )}
          {...(props as React.SelectHTMLAttributes<HTMLSelectElement>)}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    )
  },
)
Select.displayName = 'Select'
