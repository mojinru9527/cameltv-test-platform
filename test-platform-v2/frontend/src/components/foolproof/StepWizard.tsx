import { useState } from 'react'
import { Button } from '@/ui'
import { ChevronLeft, ChevronRight, Check } from '@/lib/icons'
import { cn } from '@/lib/utils'

export interface StepWizardStep {
  title: string
  description: string
  content: React.ReactNode
}

interface StepWizardProps {
  steps: StepWizardStep[]
  onFinish?: () => void
  className?: string
}

/** 3 步向导（batch-214 B4）：放东西 → AI 出结果 → 确认。 */
export function StepWizard({ steps, onFinish, className }: StepWizardProps) {
  const [index, setIndex] = useState(0)
  const isLast = index === steps.length - 1
  const step = steps[index]

  return (
    <div className={cn('space-y-4', className)}>
      <ol className="flex flex-wrap items-center gap-2 text-xs">
        {steps.map((s, i) => (
          <li key={i} className="flex items-center gap-2">
            <span
              className={cn(
                'flex size-5 shrink-0 items-center justify-center rounded-full border text-xs',
                i < index
                  ? 'border-primary text-primary'
                  : i === index
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border text-muted-foreground',
              )}
            >
              {i < index ? <Check className="size-3" /> : i + 1}
            </span>
            <span className={cn(i === index ? 'font-medium text-foreground' : 'text-muted-foreground')}>{s.title}</span>
            {i < steps.length - 1 && <span className="h-px w-6 bg-border" />}
          </li>
        ))}
      </ol>

      <div className="min-h-[240px] rounded-lg border p-4">
        <h3 className="text-sm font-medium text-foreground">{step.title}</h3>
        <p className="mt-0.5 text-xs text-muted-hc">{step.description}</p>
        <div className="mt-3">{step.content}</div>
      </div>

      <div className="flex items-center justify-between">
        <Button variant="secondary" size="sm" disabled={index === 0} onClick={() => setIndex((i) => Math.max(0, i - 1))}>
          <ChevronLeft className="size-4" />
          上一步
        </Button>
        {!isLast ? (
          <Button size="sm" onClick={() => setIndex((i) => i + 1)}>
            下一步
            <ChevronRight className="size-4" />
          </Button>
        ) : (
          <Button size="sm" onClick={() => onFinish?.()}>
            完成
            <Check className="size-4" />
          </Button>
        )}
      </div>
    </div>
  )
}

export default StepWizard

