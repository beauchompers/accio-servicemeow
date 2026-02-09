import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import Spinner from '@/components/ui/Spinner'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  children: ReactNode
  loading?: boolean
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white',
  secondary:
    'bg-[var(--bg-tertiary)] hover:bg-[var(--border)] text-[var(--text-primary)]',
  ghost: 'hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]',
  danger: 'bg-red-600 hover:bg-red-700 text-white',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      children,
      disabled,
      loading,
      className = '',
      ...rest
    },
    ref,
  ) => {
    const isDisabled = disabled || loading

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={[
          'inline-flex items-center justify-center gap-2 rounded-lg font-medium',
          'transition-all duration-200',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          variantClasses[variant],
          sizeClasses[size],
          className,
        ].join(' ')}
        {...rest}
      >
        {loading && <Spinner size="sm" />}
        {children}
      </button>
    )
  },
)

Button.displayName = 'Button'

export default Button
