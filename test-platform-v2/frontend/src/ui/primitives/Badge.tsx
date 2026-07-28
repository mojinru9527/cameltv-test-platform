import { type HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export type BadgeTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

const VARIANT_TO_TONE = {
  default: 'neutral',
  destructive: 'danger',
  outline: 'neutral',
  secondary: 'neutral',
  ghost: 'neutral',
} as const satisfies Record<string, BadgeTone>

export type BadgeVariant = keyof typeof VARIANT_TO_TONE

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  /** @deprecated Prefer `tone`; retained while existing consumers migrate. */
  variant?: BadgeVariant
}

const toneClass: Record<BadgeTone, string> = {
  success: 'ui-badge-success bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  warning: 'ui-badge-warning bg-amber-500/10 text-amber-700 dark:text-amber-400',
  danger: 'ui-badge-danger bg-destructive/10 text-destructive',
  info: 'ui-badge-info bg-sky-500/10 text-sky-700 dark:text-sky-400',
  neutral: 'ui-badge-neutral bg-secondary text-secondary-foreground',
}

function resolveTone(tone?: BadgeTone, variant?: BadgeVariant): BadgeTone {
  if (tone) return tone
  if (variant) return VARIANT_TO_TONE[variant]
  return 'neutral'
}

export function Badge({ className, tone, variant, children, ...props }: BadgeProps) {
  const resolved = resolveTone(tone, variant)
  return (
    <span
      data-slot="badge"
      data-tone={resolved}
      className={cn(
        'ui-badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-2xl border border-transparent px-2 py-0.5 text-xs font-medium whitespace-nowrap',
        'transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50',
        'aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 [&>svg]:pointer-events-none [&>svg]:size-3',
        toneClass[resolved],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}
