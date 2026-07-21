import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchKnowledgeSources } from '@/api/knowledge'
import type { KnowledgeSource } from '@/types'
import { Loader2, FolderOpen } from '@/lib/icons'

function freshnessBadge(score: number): { color: string; label: string } {
  if (score >= 0.8) return { color: 'bg-green-100 text-green-700', label: '新鲜' }
  if (score >= 0.4) return { color: 'bg-yellow-100 text-yellow-700', label: '待关注' }
  return { color: 'bg-red-100 text-red-700', label: '过期' }
}

export default function ProjectTab() {
  const [sources, setSources] = useState<KnowledgeSource[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchKnowledgeSources({ para_category: 'project', page_size: 100 })
      .then((page) => { if (!cancelled) setSources(page.items) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="grid min-h-[200px] place-items-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Group by batch name (extracted from title)
  const groups: Record<string, KnowledgeSource[]> = {}
  for (const s of sources) {
    const batch = s.title.split(' — ')[0] || '未分类'
    if (!groups[batch]) groups[batch] = []
    groups[batch].push(s)
  }

  const batches = Object.entries(groups).sort(([a], [b]) => b.localeCompare(a))

  if (batches.length === 0) {
    return (
      <div className="grid min-h-[200px] place-items-center text-sm text-muted-foreground">
        <div className="text-center space-y-2">
          <FolderOpen className="size-10 mx-auto opacity-30" />
          <p>暂无项目知识</p>
          <p className="text-xs">导入需求文档和接口文档后，项目知识将在这里展示</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>{batches.length} 个批次</span>
        <span>·</span>
        <span>{sources.length} 条知识源</span>
      </div>

      {batches.map(([batch, items]) => (
        <Card key={batch}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              <span>{batch}</span>
              <span className="text-xs text-muted-foreground">{items.length} 个工件</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {items.map((s) => {
              const badge = freshnessBadge(s.freshness_score ?? 1.0)
              return (
                <div key={s.id} className="flex items-center justify-between text-sm py-1 px-2 rounded hover:bg-muted/50 transition-colors">
                  <span className="truncate flex-1">
                    {s.title.split(' — ')[1] || s.title}
                  </span>
                  <span className="flex items-center gap-2 shrink-0 ml-2">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${badge.color}`}>
                      {badge.label}
                    </span>
                    <span className="text-xs text-muted-foreground w-16 text-right">
                      {s.created_at?.slice(0, 10) || ''}
                    </span>
                  </span>
                </div>
              )
            })}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
