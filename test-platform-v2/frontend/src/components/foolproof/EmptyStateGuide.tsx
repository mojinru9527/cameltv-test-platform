import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/ui'
import { Lightbulb, ArrowRight } from '@/lib/icons'
import { cn } from '@/lib/utils'

export interface EmptyStateGuideStep {
  text: string
  action?: { label: string; onClick: () => void }
}

interface EmptyStateGuideProps {
  stepTitle: string
  steps: EmptyStateGuideStep[]
  primaryAction?: { label: string; onClick: () => void }
  className?: string
}

/** 空态教学（batch-214 B4）：三步完成你的第一个 XX。 */
export function EmptyStateGuide({ stepTitle, steps, primaryAction, className }: EmptyStateGuideProps) {
  return (
    <Card size="sm" className={cn('border-dashed', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Lightbulb className="size-4 text-primary" />
          {stepTitle}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {steps.map((s, i) => (
          <div key={i} className="flex items-center justify-between gap-2 rounded-md border bg-muted/40 px-3 py-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-full border text-xs font-medium text-muted-foreground">
                {i + 1}
              </span>
              <span className="text-foreground">{s.text}</span>
            </div>
            {s.action && (
              <Button variant="secondary" size="sm" onClick={s.action.onClick}>
                {s.action.label}
                <ArrowRight className="size-3.5" />
              </Button>
            )}
          </div>
        ))}
        {primaryAction && (
          <div className="pt-1">
            <Button onClick={primaryAction.onClick}>{primaryAction.label}</Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default EmptyStateGuide

