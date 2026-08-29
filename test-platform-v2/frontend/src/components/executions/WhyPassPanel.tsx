import { Badge } from '@/ui'
import type { Run, Assertion, Step, Evidence } from '@/api/executions'
import { formatDuration } from './format'

export default function WhyPassPanel({
  run,
  assertions,
  steps,
  evidence,
}: {
  run: Run
  assertions: Assertion[]
  steps: Step[]
  evidence: Evidence[]
}) {
  const passCount = assertions.filter((a) => a.result === 'PASS').length
  const failedSteps = steps.filter((s) => s.status === 'FAILED').length

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="bg-status-success-muted text-status-success">
          通过
        </Badge>
        <p className="text-sm">该执行判定为通过，理由如下。</p>
      </div>
      <ul className="space-y-1 text-sm text-muted-foreground">
        <li>• 断言通过 {passCount} / {assertions.length} 条</li>
        <li>• 执行步骤 {steps.length} 步，失败 {failedSteps} 步</li>
        <li>• 采集证据 {evidence.length} 条</li>
        <li>• 用时 {formatDuration(run.duration_ms)}</li>
      </ul>
    </div>
  )
}
