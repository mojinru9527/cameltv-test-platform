import { forwardRef, type ComponentProps } from 'react'

import { Input as CanonicalInput } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export interface InputProps extends ComponentProps<typeof CanonicalInput> {
  error?: string
}

/** Compatibility adapter for legacy `error` styling and `ui-input` theme hooks. */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, ...props }, ref) => (
    <CanonicalInput
      ref={ref}
      className={cn('ui-input', error && 'is-error', className)}
      aria-invalid={error ? 'true' : props['aria-invalid']}
      {...props}
    />
  ),
)

Input.displayName = 'UiInput'
