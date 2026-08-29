import { Badge } from '@/ui'
import type { DataSourceConnectionResult } from '@/api/dataSources'

export interface DataSourceConnectionBadgeProps {
  result: DataSourceConnectionResult | null
  testing?: boolean
}

/** Connection test status badge for a data source. */
export function DataSourceConnectionBadge({ result, testing }: DataSourceConnectionBadgeProps) {
  if (testing) {
    return <Badge tone="info">测试中…</Badge>
  }
  if (!result) {
    return <Badge variant="outline">未测试</Badge>
  }
  if (!result.ok) {
    return <Badge tone="danger">连接失败</Badge>
  }
  return (
    <Badge tone="success" className="gap-1">
      已连接
      {typeof result.latency_ms === 'number' && (
        <span className="opacity-80">{result.latency_ms}ms</span>
      )}
    </Badge>
  )
}
