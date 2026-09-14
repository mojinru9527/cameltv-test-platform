import { forwardRef, type ButtonHTMLAttributes } from 'react'
import type { VariantProps } from 'class-variance-authority'

import {
  Button as CanonicalButton,
  buttonVariants,
} from '@/components/ui/button'
import { cn } from '@/lib/utils'

type CanonicalButtonVariant = VariantProps<typeof buttonVariants>['variant']
type CanonicalButtonSize = VariantProps<typeof buttonVariants>['size']

export type ButtonVariant =
  | CanonicalButtonVariant
  | 'primary'
  | 'danger'
export type ButtonSize =
  | CanonicalButtonSize
  | 'md'

type BaseButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  asChild?: boolean
}

type IconButtonProps = BaseButtonProps & {
  size: Extract<ButtonSize, 'icon' | 'icon-sm' | 'icon-xs' | 'icon-lg'>
  'aria-label': string
}

type TextButtonProps = BaseButtonProps & {
  size?: Exclude<ButtonSize, 'icon' | 'icon-sm' | 'icon-xs' | 'icon-lg'>
}

export type ButtonProps = IconButtonProps | TextButtonProps

function resolveVariant(variant: ButtonVariant): CanonicalButtonVariant {
  if (variant === 'primary') return 'default'
  if (variant === 'danger') return 'destructive'
  return variant
}

function resolveSize(size: ButtonSize): CanonicalButtonSize {
  return size === 'md' ? 'default' : size
}

/**
 * Compatibility adapter for the legacy `@/ui` button API.
 * The actual visual component and variants are canonical shadcn primitives.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'secondary',
      size = 'md',
      loading,
      disabled,
      type = 'button',
      children,
      asChild,
      ...props
    },
    ref,
  ) => {
    const legacyVariantClass = variant === 'primary' || variant === 'danger' ? `ui-btn-${variant}` : ''
    const legacySizeClass = size && size !== 'md' ? `ui-btn-${size}` : ''

    return (
      <CanonicalButton
        ref={ref}
        asChild={asChild}
        variant={resolveVariant(variant)}
        size={resolveSize(size)}
        type={type}
        className={cn('ui-btn touch-manipulation', legacyVariantClass, legacySizeClass, className)}
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
      </CanonicalButton>
    )
  },
)

Button.displayName = 'UiButton'

export { buttonVariants }
