import { type SelectHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        'ui-input flex h-10 w-full rounded-md px-3 py-2 text-sm',
        'focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
        'appearance-none bg-no-repeat bg-[length:16px] bg-[right_8px_center]',
        className,
      )}
      {...props}
    >
      {children}
    </select>
  ),
)
Select.displayName = 'Select'
