/** C119-2 — 交互拓扑覆盖缺口提示面板（Batch 120）。
 *
 * 内置模块级代表边（取自 batch-113 interaction-paths 常见入口），调用
 * POST /interaction-coverage/gaps（后端加载平台交互用例），展示覆盖率与缺口。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { interactionCoverageGaps } from '@/api/requirement'
import { Button, Input } from '@/ui'
import { Badge } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { GitCompare, RefreshCw } from '@/lib/icons'

const GAP_PAGE_SIZE = 50

interface GapItem {
  from_module: string
  entry: string
  to: string
}

interface GapResult {
  total_edges: number
  covered_edges: number
  gap_edges: number
  coverage_rate: number
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
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setError('')
    try {
      const data = await interactionCoverageGaps([], signal)  // C120-1 全量（后端 DB 拓扑）
      if (signal?.aborted) return
      setResult(data)
      setPage(1)
    } catch (e) {
      if (signal?.aborted) return
      const msg = e instanceof Error ? e.message : '缺口计算失败'
      setError(msg)
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal)
    return () => controller.abort()
  }, [load])

  const rate = result?.coverage_rate ?? 0
  const rateLabel = `${(rate * 100).toFixed(1)}%`
  const filteredGaps = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return result?.gaps || []
    return (result?.gaps || []).filter((gap) =>
      [gap.from_module, gap.entry, gap.to].some((value) => value.toLowerCase().includes(normalized)),
    )
  }, [query, result?.gaps])
  const pageCount = Math.max(1, Math.ceil(filteredGaps.length / GAP_PAGE_SIZE))
  const pagedGaps = filteredGaps.slice((page - 1) * GAP_PAGE_SIZE, page * GAP_PAGE_SIZE)

  useEffect(() => {
    setPage(1)
  }, [query])

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
            <Button size="sm" variant="secondary" onClick={() => { void load() }}>
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
              <Button size="sm" variant="ghost" onClick={() => { void load() }} aria-label="刷新交互缺口">
                <RefreshCw className="size-3.5" />
              </Button>
            </div>
            {result.gaps.length === 0 ? (
              <p className="text-xs text-muted-foreground py-4 text-center">暂无覆盖缺口</p>
            ) : (
              <div className="space-y-2">
                <Input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="按模块、入口或目标筛选"
                  aria-label="筛选交互缺口"
                  className="h-8 text-xs"
                />
                {filteredGaps.length === 0 ? (
                  <p className="py-4 text-center text-xs text-muted-foreground">没有匹配的交互缺口</p>
                ) : (
                  <div className="border rounded-lg overflow-auto max-h-[220px]">
                    <ul className="divide-y">
                  {pagedGaps.map((g, i) => (
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
                {filteredGaps.length > GAP_PAGE_SIZE && (
                  <div className="flex items-center justify-between">
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={page === 1}
                      onClick={() => setPage((current) => Math.max(1, current - 1))}
                      aria-label="上一页缺口"
                    >
                      上一页
                    </Button>
                    <span className="text-xs tabular-nums text-muted-foreground">第 {page} / {pageCount} 页</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={page === pageCount}
                      onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
                      aria-label="下一页缺口"
                    >
                      下一页
                    </Button>
                  </div>
                )}
              </div>
            )}
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}
