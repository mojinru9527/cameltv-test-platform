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
  positive: 'border-l-[#35e68a]/20',
  active: 'border-l-[#80c4ff]/20',
  risk: 'border-l-[#ff9a90]/20',
  neutral: 'border-l-[#718077]/20',
}

const toneText: Record<MetricTone, string> = {
  positive: 'text-[#80dba6]',
  active: 'text-[#80c4ff]',
  risk: 'text-[#ff9a90]',
  neutral: 'text-[#909f95]',
}

export function MetricStrip({ metrics, className }: MetricStripProps) {
  return (
    <div
      className={cn(
        'grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))]',
        'border-y border-[rgba(218,239,224,0.08)]',
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
            i > 0 && 'border-l border-[rgba(218,239,224,0.08)]',
            i === 0 && 'pl-0',
          )}
        >
          <span className={cn('flex items-center gap-[7px] text-xs', toneText[m.tone])}>
            {m.icon}
            {m.label}
          </span>
          <b className="row-span-2 col-start-2 self-center text-[1.75rem] font-[560] tracking-tight text-[#eef6f0]">
            {m.value}
          </b>
          <small className="text-[0.75rem] text-[#718077]">{m.note}</small>
        </div>
      ))}
    </div>
  )
}
