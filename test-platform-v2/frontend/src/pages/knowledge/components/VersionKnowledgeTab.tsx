import { useMemo } from 'react'
import { useApi } from '@/hooks/useApi'
import { fetchVersionKnowledge, type VersionKnowledgeRecord } from '@/api/knowledge'
import { AsyncState } from '@/components/state'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

/**
 * B11 知识闭环：版本记录 / 复用建议 Tab。
 * 数据源：版本任务放行后沉淀的 VersionKnowledgeRecord（/knowledge/version-records）。
 */
export default function VersionKnowledgeTab({ mode }: { mode: 'records' | 'reuse' }) {
  const { data, isLoading, isError, error, refetch } = useApi<VersionKnowledgeRecord[]>(
    (signal) => fetchVersionKnowledge(signal),
  )
  const list = useMemo(() => data ?? [], [data])

  const renderRecord = (r: VersionKnowledgeRecord) => {
    const cov = r.coverage || {}
    const pass = cov.pass ?? 0
    const total = (cov.pass ?? 0) + (cov.fail ?? 0) + (cov.skip ?? 0) + (cov.blocked ?? 0)
    const rate = total > 0 ? Math.round((pass * 100) / total) : 0
    return (
      <Card key={r.id} className="mt-2">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Badge variant="outline">{r.version}</Badge>
            <span>{r.title}</span>
            {r.verdict && <Badge variant={r.verdict === 'pass' ? 'default' : 'secondary'}>{r.verdict}</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          <p className="text-xs text-muted-foreground">{r.summary || '（无摘要）'}</p>
          <p className="text-xs text-muted-foreground">
            覆盖 {total} 项 · 通过率 {rate}% · 缺陷 {r.defect_count}
          </p>
          {mode === 'reuse' && (
            <div className="rounded bg-muted/50 p-2 text-xs">
              <span className="font-medium">复用建议：</span>
              {Array.isArray(r.plan_summary) && r.plan_summary.length > 0
                ? (r.plan_summary as string[]).join('；')
                : '方案已沉淀为版本任务，下版建任务时可一键引用。'}
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <AsyncState
      isLoading={isLoading}
      isError={isError}
      error={error}
      data={data}
      onRetry={refetch}
      loadingText="正在加载版本知识记录"
      skeletonType="card"
      loadingRows={3}
    >
      {() =>
        list.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {mode === 'records' ? '暂无版本知识记录（版本任务放行后自动沉淀）。' : '暂无复用建议（完成一个版本任务后生成）。'}
          </p>
        ) : (
          <div>{list.map(renderRecord)}</div>
        )
      }
    </AsyncState>
  )
}
