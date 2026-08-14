import { parseUiRunResult } from '../uiRunResult'

export default function UiRunResultSummary({ value }: { value: unknown }) {
  const summary = parseUiRunResult(value)
  if (!summary) {
    return (
      <pre className="m-0 whitespace-pre-wrap text-xs">
        {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
      </pre>
    )
  }

  const metrics = [
    ['总计', summary.total],
    ['通过', summary.passed],
    ['失败', summary.failed],
    ['跳过', summary.skipped],
  ] as const
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {metrics.map(([label, value]) => (
          <div key={label} className="rounded-md border bg-muted/30 p-3 text-center">
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className="mt-1 text-lg font-semibold tabular-nums">{value}</div>
          </div>
        ))}
      </div>
      {summary.duration !== null && (
        <p className="text-xs text-muted-foreground">执行耗时：{summary.duration} 秒</p>
      )}
    </div>
  )
}
