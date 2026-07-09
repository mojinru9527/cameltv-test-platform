import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchKnowledgeOverview } from '@/api/knowledge'
import type { KnowledgeOverview } from '@/types'
import { Loader2 } from '@/lib/icons'

const SOURCE_TYPE_LABELS: Record<string, string> = {
  requirement: '需求',
  openapi: '接口导入',
  test_case: '接口用例',
  defect: '缺陷',
  execution: '执行失败',
  manual: '手动',
}

export default function OverviewTab() {
  const [data, setData] = useState<KnowledgeOverview | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchKnowledgeOverview()
      .then((data) => { if (!cancelled) { setData(data); setLoading(false) } })
      .catch(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="grid min-h-[200px] place-items-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }
  if (!data) return <div className="text-sm text-muted-foreground">概览加载失败</div>

  const stats = [
    { label: '知识源', value: data.source_count },
    { label: '知识切片', value: data.chunk_count },
    { label: '图谱实体', value: data.entity_count },
    { label: '待审 AI 产物', value: data.pending_artifact_count },
  ]
  const health = [
    { label: '未审核 AI 产物', value: data.health.unreviewed_artifacts },
    { label: '已废弃知识源', value: data.health.deprecated_sources },
    { label: '孤儿切片', value: data.health.sourceless_chunks },
    { label: '低置信度关系', value: data.health.low_confidence_relations },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-4">
              <div className="text-2xl font-semibold">{s.value}</div>
              <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">知识健康度</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {health.map((h) => (
              <div key={h.label} className="rounded-md border p-3">
                <div className="text-lg font-medium">{h.value}</div>
                <div className="text-xs text-muted-foreground mt-1">{h.label}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {data.recent_sources.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">最近知识源</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.recent_sources.map((s) => (
              <div key={s.id} className="flex items-center justify-between text-sm gap-2">
                <span className="truncate">
                  <span className="text-muted-foreground">
                    {SOURCE_TYPE_LABELS[s.source_type] ?? s.source_type}
                  </span>{' '}
                  · {s.title}
                </span>
                <span className="text-xs text-muted-foreground shrink-0">
                  {s.created_at?.slice(0, 10)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
