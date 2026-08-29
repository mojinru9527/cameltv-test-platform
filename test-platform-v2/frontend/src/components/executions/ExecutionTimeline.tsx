import { Badge } from '@/ui'
import type { Step } from '@/api/executions'
import { STEP_STATUS_LABELS } from './constants'

function SnapshotView({
  label,
  value,
}: {
  label: string
  value: Record<string, unknown> | null | undefined
}) {
  if (!value) return null
  let text: string
  try {
    text = JSON.stringify(value, null, 2)
  } catch {
    text = String(value)
  }
  return (
    <details className="rounded-lg border p-2">
      <summary className="cursor-pointer text-xs text-muted-foreground">{label}</summary>
      <pre className="mt-2 max-h-64 overflow-auto rounded bg-muted p-2 text-xs">{text}</pre>
    </details>
  )
}

export default function ExecutionTimeline({ steps }: { steps: Step[] }) {
  if (steps.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">暂无执行步骤。</p>
  }
  return (
    <ol className="space-y-3">
      {steps.map((step) => {
        const st = STEP_STATUS_LABELS[step.status]
        return (
          <li key={step.id} className="rounded-lg border p-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-muted-foreground">#{step.sequence}</span>
              <span className="font-medium">{step.step_key}</span>
              <Badge variant="outline">{step.step_type}</Badge>
              <Badge variant="secondary" className={st?.color}>
                {st?.label ?? step.status}
              </Badge>
            </div>
            {step.error_type && (
              <p className="mt-1 text-xs font-medium text-status-danger">{step.error_type}</p>
            )}
            {step.error_message && (
              <p className="mt-1 text-sm text-status-danger">{step.error_message}</p>
            )}
            {(step.started_at || step.finished_at) && (
              <p className="mt-1 text-xs text-muted-foreground">
                {step.started_at ?? '—'} → {step.finished_at ?? '—'}
              </p>
            )}
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <SnapshotView label="输入快照" value={step.input_snapshot_json} />
              <SnapshotView label="输出快照" value={step.output_snapshot_json} />
            </div>
          </li>
        )
      })}
    </ol>
  )
}
