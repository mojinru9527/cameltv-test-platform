import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { fetchKnowledgeSources, verifyKnowledgeSource } from '@/api/knowledge'
import type { KnowledgeSource } from '@/types'
import { Loader2, Sparkles, BookOpen, Inbox, CheckCircle2 } from '@/lib/icons'
import { toast } from 'sonner'

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
  const [verifying, setVerifying] = useState<Set<number>>(new Set())

  const load = useCallback(() => {
    fetchKnowledgeSources({ knowledge_domain: 'platform', page_size: 200 })
      .then((page) => setSources(page.items))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleVerify = async (sourceId: number, e: React.MouseEvent) => {
    e.stopPropagation()
    setVerifying((prev) => new Set(prev).add(sourceId))
    try {
      const updated = await verifyKnowledgeSource(sourceId)
      setSources((prev) =>
        prev.map((s) => (s.id === sourceId ? { ...s, ...updated } : s))
      )
      toast.success('已验证')
    } catch {
      toast.error('验证失败')
    } finally {
      setVerifying((prev) => {
        const next = new Set(prev)
        next.delete(sourceId)
        return next
      })
    }
  }

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
                <div key={s.id} className="flex items-center justify-between text-sm py-1 px-2 rounded hover:bg-muted/50 transition-colors group">
                  <span className="truncate flex-1">{s.title}</span>
                  <span className="flex items-center gap-2 shrink-0 ml-2">
                    <span
                      className={`inline-block size-2 rounded-full ${freshnessColor(s.freshness_score ?? 1.0)}`}
                      title={`保鲜评分: ${((s.freshness_score ?? 1.0) * 100).toFixed(0)}%`}
                    />
                    <span className="text-xs text-muted-foreground w-14 text-right">
                      {daysAgo(s.last_verified_at)}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      disabled={verifying.has(s.id)}
                      onClick={(e) => handleVerify(s.id, e)}
                      title="验证此知识源"
                    >
                      <CheckCircle2 className="size-3.5" />
                    </Button>
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
