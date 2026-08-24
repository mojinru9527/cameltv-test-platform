import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export type MetricTone = 'positive' | 'active' | 'risk' | 'neutral'

export interface MetricItem {
  icon: ReactNode
  label: string
  value: string
  note: string
  tone: MetricTone
}

export interface MetricStripProps {
  metrics: MetricItem[]
  className?: string
}

const toneBorder: Record<MetricTone, string> = {
  positive: 'border-l-obsidian-tone-positive/20',
  active: 'border-l-obsidian-tone-active/20',
  risk: 'border-l-obsidian-tone-risk/20',
  neutral: 'border-l-obsidian-tone-neutral/20',
}

const toneText: Record<MetricTone, string> = {
  positive: 'text-obsidian-tone-positive',
  active: 'text-obsidian-tone-active',
  risk: 'text-obsidian-tone-risk',
  neutral: 'text-obsidian-tone-neutral',
}

export function MetricStrip({ metrics, className }: MetricStripProps) {
  return (
    <div
      className={cn(
        'grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))]',
        'border-y border-obsidian-border-soft',
        'py-3',
        className,
      )}
      aria-label="关键指标"
    >
      {metrics.map((m, i) => (
        <div
          key={m.label}
          className={cn(
            'relative grid grid-cols-[1fr_auto] gap-x-3 gap-y-[5px]',
            'min-w-0 px-6 py-2',
            i > 0 && 'border-l border-obsidian-border-soft',
            i === 0 && 'pl-0',
          )}
        >
          <span className={cn('flex items-center gap-[7px] text-xs', toneText[m.tone])}>
            {m.icon}
            {m.label}
          </span>
          <b className="row-span-2 col-start-2 self-center text-[1.75rem] font-[560] tracking-tight text-foreground">
            {m.value}
          </b>
          <small className="text-caption text-muted-foreground">{m.note}</small>
        </div>
      ))}
    </div>
  )
}