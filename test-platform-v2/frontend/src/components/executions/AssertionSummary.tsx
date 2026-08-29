import { Badge } from '@/ui'
import type { Assertion } from '@/api/executions'
import { ASSERTION_RESULT_LABELS } from './constants'

export default function AssertionSummary({ assertions }: { assertions: Assertion[] }) {
  const counts: Record<string, number> = {}
  for (const a of assertions) {
    counts[a.result] = (counts[a.result] ?? 0) + 1
  }
  const total = assertions.length

  if (total === 0) {
    return <p className="text-sm text-muted-foreground">暂无断言。</p>
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-muted-foreground">
        共 <span className="font-medium text-foreground">{total}</span> 条断言
      </p>
      <div className="flex flex-wrap gap-2">
        {Object.entries(counts).map(([result, count]) => {
          const meta = ASSERTION_RESULT_LABELS[result]
          return (
            <Badge key={result} variant="secondary" className={meta?.color}>
              {meta?.label ?? result} {count}
            </Badge>
          )
        })}
      </div>
    </div>
  )
}
