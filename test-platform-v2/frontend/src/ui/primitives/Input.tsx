import { type InputHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn('ui-input', error && 'is-error', className)}
        aria-invalid={error ? 'true' : undefined}
        {...props}
      />
    )
  },
)

Input.displayName = 'UiInput'
