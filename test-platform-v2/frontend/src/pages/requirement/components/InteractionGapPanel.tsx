/** C119-2 — 交互拓扑覆盖缺口提示面板（Batch 120）。
 *
 * 内置模块级代表边（取自 batch-113 interaction-paths 常见入口），调用
 * POST /interaction-coverage/gaps（后端加载平台交互用例），展示覆盖率与缺口。
 */
import { useCallback, useEffect, useState } from 'react'
import { interactionCoverageGaps } from '@/api/requirement'
import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { GitCompare, RefreshCw } from '@/lib/icons'

interface GapItem {
  from_module: string
  entry: string
  to: string
}

interface GapResult {
  summary: { total_edges: number; covered_edges: number; gap_edges: number; coverage_rate: number }
  gaps: GapItem[]
}

function toLabel(url: string): string {
  const clean = url.replace(/^https?:\/\//, '').split('?')[0]
  return clean.length > 60 ? `${clean.slice(0, 57)}...` : clean
}

export default function InteractionGapPanel() {
  const [loading, setLoading] = useState(true)
  const [result, setResult] = useState<GapResult | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await interactionCoverageGaps([])  // C120-1 全量（后端 DB 拓扑）
      setResult(data)
    } catch (e) {
      const msg = e instanceof Error ? e.message : '缺口计算失败'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const rate = result?.coverage_rate ?? 0
  const rateLabel = `${(rate * 100).toFixed(1)}%`

  return (
    <Card size="sm" className="ui-surface">
      <CardHeader className="border-b pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <GitCompare className="size-4" />
          交互覆盖缺口（C119-2）
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4 space-y-3">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-xs text-status-danger">{error}</span>
            <Button size="sm" variant="secondary" onClick={load}>
              <RefreshCw className="size-3.5" />
              重试
            </Button>
          </div>
        ) : result ? (
          <>
            <div className="flex items-center gap-3 flex-wrap">
              <Badge
                tone="neutral"
                className={rate >= 0.5
                  ? 'border-status-success-border bg-status-success-muted text-status-success'
                  : 'border-status-warning-border bg-status-warning-muted text-status-warning'}
              >
                覆盖率 {rateLabel}
              </Badge>
              <span className="text-xs text-muted-foreground">
                已覆盖 {result.covered_edges}/{result.total_edges} 边 · 缺口 {result.gap_edges}
              </span>
              <Button size="sm" variant="ghost" onClick={load} aria-label="刷新交互缺口">
                <RefreshCw className="size-3.5" />
              </Button>
            </div>
            {result.gaps.length === 0 ? (
              <p className="text-xs text-muted-foreground py-4 text-center">暂无覆盖缺口</p>
            ) : (
              <div className="border rounded-lg overflow-auto max-h-[220px]">
                <ul className="divide-y">
                  {result.gaps.slice(0, 50).map((g, i) => (
                    <li key={`${g.from_module}-${g.to}-${i}`} className="flex items-center gap-2 px-3 py-1.5">
                      <Badge tone="neutral" className="border-status-warning-border bg-status-warning-muted text-status-warning shrink-0">
                        缺口
                      </Badge>
                      <span className="text-xs font-medium shrink-0">{g.from_module || '-'}</span>
                      <span className="text-[11px] text-muted-foreground truncate" title={g.to}>
                        {g.entry || ''} → {toLabel(g.to)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}
