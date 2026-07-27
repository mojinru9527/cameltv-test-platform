import { type HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export type ProgressTone = 'success' | 'warning' | 'danger'

export interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value: number
  max?: number
  tone?: ProgressTone
}

export function Progress({
  className,
  value,
  max = 100,
  tone = 'success',
  ...props
}: ProgressProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))

  const fillClass = {
    success: 'ui-progress-fill',
    warning: 'ui-progress-fill is-warning',
    danger: 'ui-progress-fill is-danger',
  }[tone]

  return (
    <div
      className={cn('ui-progress', className)}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      {...props}
    >
      <span className={fillClass} style={{ width: `${pct}%` }} />
    </div>
  )
}
