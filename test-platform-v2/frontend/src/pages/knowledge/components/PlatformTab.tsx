import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchKnowledgeSources } from '@/api/knowledge'
import type { KnowledgeSource } from '@/types'
import { Loader2, Sparkles, BookOpen, Inbox } from '@/lib/icons'

const PARA_LABELS: Record<string, { label: string; icon: typeof Sparkles }> = {
  area: { label: '问题模式 / 长期领域', icon: Sparkles },
  resource: { label: '设计规范 / 审查报告', icon: BookOpen },
  archive: { label: '归档', icon: Inbox },
}

function freshnessColor(score: number): string {
  if (score >= 0.8) return 'bg-green-500'
  if (score >= 0.4) return 'bg-yellow-500'
  return 'bg-red-500'
}

function daysAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return '未验证'
  const d = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24))
  if (diff === 0) return '今天'
  if (diff === 1) return '1天前'
  return `${diff}天前`
}

export default function PlatformTab() {
  const [sources, setSources] = useState<KnowledgeSource[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchKnowledgeSources({ knowledge_domain: 'platform', page_size: 200 })
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

  // Group by para_category
  const groups: Record<string, KnowledgeSource[]> = {}
  for (const s of sources) {
    const cat = s.para_category || 'inbox'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(s)
  }

  // Order: area > resource > archive > inbox
  const categoryOrder = ['area', 'resource', 'archive', 'inbox', 'project', 'wiki', 'skill']
  const sorted = Object.entries(groups).sort(
    ([a], [b]) => categoryOrder.indexOf(a) - categoryOrder.indexOf(b)
  )

  if (sorted.length === 0) {
    return (
      <div className="grid min-h-[200px] place-items-center text-sm text-muted-foreground">
        <div className="text-center space-y-2">
          <Sparkles className="size-10 mx-auto opacity-30" />
          <p>暂无平台研发知识</p>
          <p className="text-xs">Agent Team 任务完成后，研发知识将自动沉淀到这里</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>{sorted.length} 个分区</span>
        <span>·</span>
        <span>{sources.length} 条知识源</span>
      </div>

      {sorted.map(([cat, items]) => {
        const meta = PARA_LABELS[cat] || { label: cat, icon: BookOpen }
        const Icon = meta.icon
        return (
          <Card key={cat}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Icon className="size-4 text-muted-foreground" />
                <span>{meta.label}</span>
                <span className="text-xs text-muted-foreground font-normal">{items.length}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {items.map((s) => (
                <div key={s.id} className="flex items-center justify-between text-sm py-1 px-2 rounded hover:bg-muted/50 transition-colors">
                  <span className="truncate flex-1">{s.title}</span>
                  <span className="flex items-center gap-2 shrink-0 ml-2">
                    <span
                      className={`inline-block size-2 rounded-full ${freshnessColor(s.freshness_score ?? 1.0)}`}
                      title={`保鲜评分: ${((s.freshness_score ?? 1.0) * 100).toFixed(0)}%`}
                    />
                    <span className="text-xs text-muted-foreground w-14 text-right">
                      {daysAgo(s.last_verified_at)}
                    </span>
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
