import { Badge } from '@/ui'
import { OUTCOME_LABELS } from '@/api/executions'
import type { Run, Assertion, Step } from '@/api/executions'

export default function FailureClassificationPanel({
  run,
  steps,
  assertions,
}: {
  run: Run
  steps: Step[]
  assertions: Assertion[]
}) {
  const failedSteps = steps.filter((s) => s.status === 'FAILED')
  const failedAssertions = assertions.filter((a) => a.result === 'FAIL')
  const outcomeMeta = OUTCOME_LABELS[run.outcome ?? '']

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className={outcomeMeta?.color}>
          {outcomeMeta?.label ?? run.outcome ?? '失败'}
        </Badge>
        <p className="text-sm">该执行判定为失败，归类分析如下。</p>
      </div>

      {failedSteps.length > 0 && (
        <div>
          <p className="text-sm font-medium">失败步骤</p>
          <ul className="mt-1 space-y-1">
            {failedSteps.map((s) => (
              <li key={s.id} className="text-sm">
                <span className="font-mono text-xs text-muted-foreground">#{s.sequence}</span>{' '}
                {s.step_key}
                {s.error_type && <span className="ml-2 text-status-danger">{s.error_type}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {failedAssertions.length > 0 && (
        <div>
          <p className="text-sm font-medium">失败断言</p>
          <ul className="mt-1 space-y-1">
            {failedAssertions.map((a) => (
              <li key={a.id} className="text-sm">
                Oracle #{a.oracle_id} · {a.reason_code}
              </li>
            ))}
          </ul>
        </div>
      )}

      {failedSteps.length === 0 && failedAssertions.length === 0 && (
        <p className="text-sm text-muted-foreground">
          失败原因未在步骤/断言中明确记录，请结合证据与回放排查。
        </p>
      )}
    </div>
  )
}
