import { Badge } from '@/ui'
import type { Assertion } from '@/api/executions'
import { ASSERTION_RESULT_LABELS } from './constants'
import { OracleSourceBadge } from '@/components/trust/OracleSourceBadge'

function oracleName(a: Assertion): string {
  const snap = a.oracle_snapshot_json
  if (snap && typeof snap === 'object') {
    const key = (snap as Record<string, unknown>).oracle_key ?? (snap as Record<string, unknown>).target
    if (typeof key === 'string') return key
  }
  return `Oracle #${a.oracle_id}`
}

export default function RequiredOracleList({ assertions }: { assertions: Assertion[] }) {
  if (assertions.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">未记录 Oracle 断言。</p>
  }
  return (
    <ul className="space-y-2">
      {assertions.map((a) => {
        const meta = ASSERTION_RESULT_LABELS[a.result]
        return (
          <li key={a.id} className="rounded-lg border p-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary" className={meta?.color}>
                {meta?.label ?? a.result}
              </Badge>
              <span className="font-medium">{oracleName(a)}</span>
              <span className="font-mono text-xs text-muted-foreground">#{a.oracle_id}</span>
              <OracleSourceBadge assertion={a} />
            </div>
            {a.reason_code && (
              <p className="mt-1 text-xs text-muted-foreground">reason: {a.reason_code}</p>
            )}
          </li>
        )
      })}
    </ul>
  )
}
