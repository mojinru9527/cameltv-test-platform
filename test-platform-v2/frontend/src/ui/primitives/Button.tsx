import { type ButtonHTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg' | 'icon' | 'icon-sm' | 'icon-xs'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
}

const variantClassMap: Record<ButtonVariant, string> = {
  primary: 'ui-btn-primary bg-primary text-primary-foreground hover:bg-primary/90',
  secondary: 'ui-btn-secondary border-input bg-background text-foreground hover:bg-accent hover:text-accent-foreground',
  ghost: 'ui-btn-ghost text-foreground hover:bg-accent hover:text-accent-foreground',
  danger: 'ui-btn-danger bg-destructive text-destructive-foreground hover:bg-destructive/90',
}

const sizeClassMap: Record<ButtonSize, string> = {
  xs: 'ui-btn-xs h-6 gap-1 rounded-lg px-2 text-xs [&_svg:not([class*="size-"])]:size-3',
  sm: 'ui-btn-sm h-7 gap-1 rounded-lg px-2.5 text-[0.8rem] [&_svg:not([class*="size-"])]:size-3.5',
  md: 'h-8 gap-1.5 px-2.5',
  lg: 'ui-btn-lg h-9 gap-1.5 px-3',
  icon: 'ui-btn-icon size-8',
  'icon-sm': 'ui-btn-icon-sm size-7 rounded-lg',
  'icon-xs': 'ui-btn-icon-xs size-6 rounded-lg [&_svg:not([class*="size-"])]:size-3',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'secondary', size = 'md', loading, disabled, type = 'button', children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        data-slot="button"
        data-variant={variant}
        data-size={size}
        type={type}
        className={cn(
          'ui-btn inline-flex shrink-0 touch-manipulation items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-colors outline-none select-none',
          'focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:translate-y-px',
          'disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20',
          '[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*="size-"])]:size-4',
          variantClassMap[variant],
          sizeClassMap[size],
          className,
        )}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading ? (
          <>
            <span
              className="ui-spinner size-4 animate-spin rounded-full border-2 border-current border-r-transparent"
              aria-hidden="true"
            />
            <span>{children}</span>
          </>
        ) : (
          children
        )}
      </button>
    )
  },
)

Button.displayName = 'UiButton'
