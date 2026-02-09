type SpinnerSize = 'sm' | 'md' | 'lg'

interface SpinnerProps {
  size?: SpinnerSize
}

const sizeClasses: Record<SpinnerSize, string> = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-3',
}

export default function Spinner({ size = 'md' }: SpinnerProps) {
  return (
    <div
      className={[
        'animate-spin rounded-full',
        'border-[var(--accent)] border-t-transparent',
        sizeClasses[size],
      ].join(' ')}
      role="status"
      aria-label="Loading"
    />
  )
}
