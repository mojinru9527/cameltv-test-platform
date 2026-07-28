import { type HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export type BadgeTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

/**
 * shadcn → @/ui variant→tone 兼容映射
 * 允许消费者继续传 variant，内部自动转 tone
 */
const VARIANT_TO_TONE: Record<string, BadgeTone> = {
  default: 'neutral',
  destructive: 'danger',
  outline: 'neutral',
  secondary: 'neutral',
  ghost: 'neutral',
}

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  /** shadcn/ui 兼容 alias — 自动映射为 tone（tone 优先级更高） */
  variant?: string
}

const toneClass: Record<BadgeTone, string> = {
  success: 'ui-badge-success',
  warning: 'ui-badge-warning',
  danger: 'ui-badge-danger',
  info: 'ui-badge-info',
  neutral: 'ui-badge-neutral',
}

function resolveTone(tone?: BadgeTone, variant?: string): BadgeTone {
  if (tone) return tone
  if (variant && VARIANT_TO_TONE[variant]) return VARIANT_TO_TONE[variant]
  return 'neutral'
}

export function Badge({ className, tone, variant, children, ...props }: BadgeProps) {
  const resolved = resolveTone(tone, variant)
  return (
    <span className={cn('ui-badge', toneClass[resolved], className)} {...props}>
      {children}
    </span>
  )
}
