import { Progress } from '@/ui'
import { WORKFLOW_STATUS_LABELS, type WorkflowRun } from '@/api/runtime'

// Ordered path of a Durable Run across its runtime states (plan §10).
const ORDER: string[] = ['SCHEDULED', 'RUNNING', 'WAITING_WORKER', 'WAITING_APPROVAL', 'RETRYING', 'RESUMING', 'FINISHED', 'FAILED', 'CANCELLED']

/** A progress bar that reflects how far a Run is through its runtime lifecycle. */
export function WorkflowProgress({ run }: { run: WorkflowRun }) {
  const status = run.status
  const label = WORKFLOW_STATUS_LABELS[status]?.label ?? status
  const idx = ORDER.indexOf(status)
  const pct = idx < 0 ? 0 : Math.round(((idx + 1) / ORDER.length) * 100)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <Progress value={pct} />
    </div>
  )
}
