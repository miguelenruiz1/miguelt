import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success' | 'outline'
type Size    = 'sm' | 'md' | 'lg' | 'icon'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
}

const variants: Record<Variant, string> = {
  primary:   'bg-indigo-500 hover:bg-indigo-600 text-white shadow-sm',
  secondary: 'bg-gray-100 hover:bg-gray-200 text-gray-700 border border-gray-200',
  ghost:     'hover:bg-gray-100 text-gray-600 hover:text-gray-700',
  danger:    'bg-red-500 hover:bg-red-600 text-white shadow-sm',
  success:   'bg-emerald-500 hover:bg-emerald-600 text-white shadow-sm',
  outline:   'border border-gray-300 hover:border-indigo-500 text-gray-700 hover:text-indigo-600 bg-white',
}

const sizes: Record<Size, string> = {
  sm:   'h-8  px-3 text-xs  gap-1.5',
  md:   'h-9  px-4 text-sm  gap-2',
  lg:   'h-10 px-5 text-sm  gap-2',
  icon: 'h-9  w-9 text-sm',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled ?? loading}
      className={cn(
        'inline-flex items-center justify-center font-medium rounded-lg',
        'transition-all duration-150 cursor-pointer',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 100 16v-4l-3 3 3 3v-4a8 8 0 01-8-8z" />
        </svg>
      )}
      {children}
    </button>
  ),
)
Button.displayName = 'Button'
