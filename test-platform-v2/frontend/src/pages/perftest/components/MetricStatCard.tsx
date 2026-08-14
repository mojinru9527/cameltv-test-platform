import { CheckCircle2, XCircle } from '@/lib/icons'
import { METRIC_LABELS, METRIC_UNITS } from './perfShared'
import type { MetricStatsItem } from '@/api/perftest'

export default function MetricStatCard({ stat }: { stat: MetricStatsItem }) {
  const label = METRIC_LABELS[stat.metric_type] ?? stat.metric_type
  const unit = stat.unit || METRIC_UNITS[stat.metric_type] || ''
  return (
    <div className={`rounded-lg border p-3 ${
      stat.passed ? 'border-status-success-border bg-status-success-muted dark:bg-status-success-muted' : 'border-status-danger-border bg-status-danger-muted dark:bg-status-danger-muted'
    }`}>
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-xs font-medium">{label}</span>
        {stat.passed ? <CheckCircle2 className="size-3 text-status-success" /> : <XCircle className="size-3 text-status-danger" />}
      </div>
      <p className="text-2xl font-bold tabular-nums">
        {stat.mean}
        <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>
      </p>
      <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
        <span>中位: {stat.median}</span>
        <span>P95: {stat.p95}</span>
        <span>最小: {stat.min_val}</span>
        <span>最大: {stat.max_val}</span>
        <span className="col-span-2">样本: {stat.samples} · SD: {stat.stddev}</span>
      </div>
    </div>
  )
}
