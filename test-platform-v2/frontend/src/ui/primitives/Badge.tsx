import type { ComponentProps } from 'react'

import {
  Badge as CanonicalBadge,
  badgeVariants,
} from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { VariantProps } from 'class-variance-authority'

export type BadgeTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral'
export type BadgeVariant = VariantProps<typeof badgeVariants>['variant']

const toneClass: Record<BadgeTone, string> = {
  success: 'ui-badge-success bg-status-success-muted text-status-success',
  warning: 'ui-badge-warning bg-status-warning-muted text-status-warning',
  danger: 'ui-badge-danger bg-status-danger-muted text-status-danger',
  info: 'ui-badge-info bg-status-info-muted text-status-info',
  neutral: 'ui-badge-neutral bg-secondary text-secondary-foreground',
}

export interface BadgeProps extends ComponentProps<typeof CanonicalBadge> {
  tone?: BadgeTone
  variant?: BadgeVariant
}

/**
 * Compatibility adapter for the legacy semantic `tone` API.
 * Tone classes now decorate the canonical shadcn Badge implementation.
 */
export function Badge({
  className,
  tone,
  variant = 'secondary',
  children,
  ...props
}: BadgeProps) {
  const resolvedVariant = tone ? 'secondary' : variant
  const resolvedToneClass = tone ? toneClass[tone] : ''

  return (
    <CanonicalBadge
      variant={resolvedVariant}
      className={cn(resolvedToneClass, className)}
      {...props}
    >
      {children}
    </CanonicalBadge>
  )
}

export { badgeVariants }
