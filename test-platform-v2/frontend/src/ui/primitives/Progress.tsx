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
  const safeMax = Number.isFinite(max) && max > 0 ? max : 100
  const safeValue = Number.isFinite(value) ? Math.min(safeMax, Math.max(0, value)) : 0
  const scale = safeValue / safeMax

  const fillClass = {
    success: 'ui-progress-fill bg-primary',
    warning: 'ui-progress-fill is-warning bg-amber-500',
    danger: 'ui-progress-fill is-danger bg-destructive',
  }[tone]

  return (
    <div
      data-slot="progress"
      className={cn('ui-progress relative h-1 w-full overflow-hidden rounded-full bg-muted', className)}
      role="progressbar"
      aria-valuenow={safeValue}
      aria-valuemin={0}
      aria-valuemax={safeMax}
      {...props}
    >
      <span
        data-slot="progress-indicator"
        className={cn('block size-full origin-left transition-transform duration-200 ease-out', fillClass)}
        style={{
          transform: `scaleX(${scale})`,
          transformOrigin: 'left',
          transitionProperty: 'transform',
        }}
      />
    </div>
  )
}
