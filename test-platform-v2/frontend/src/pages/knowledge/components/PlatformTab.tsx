import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { fetchKnowledgeSources, fetchSourceChunks, verifyKnowledgeSource } from '@/api/knowledge'
import type { KnowledgeChunk, KnowledgeSource } from '@/types'
import { Loader2, Sparkles, BookOpen, Inbox, CheckCircle2, ChevronDown, ChevronRight } from '@/lib/icons'
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

  // ── 分区折叠状态（默认展开 area）──
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['area']))

  // ── 详情弹窗状态 ──
  const [selected, setSelected] = useState<KnowledgeSource | null>(null)
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)

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

  const togglePartition = (cat: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(cat)) next.delete(cat)
      else next.add(cat)
      return next
    })
  }

  const viewChunks = (src: KnowledgeSource) => {
    setSelected(src)
    setChunksLoading(true)
    setChunks([])
    fetchSourceChunks(src.id)
      .then(setChunks)
      .catch(() => setChunks([]))
      .finally(() => setChunksLoading(false))
  }

  const closeDetail = () => {
    setSelected(null)
    setChunks([])
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
        const isExpanded = expanded.has(cat)
        return (
          <Card key={cat}>
            <CardHeader
              className="pb-2 cursor-pointer hover:bg-muted/30 transition-colors rounded-t-lg"
              onClick={() => togglePartition(cat)}
            >
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                {isExpanded ? (
                  <ChevronDown className="size-4 text-muted-foreground shrink-0" />
                ) : (
                  <ChevronRight className="size-4 text-muted-foreground shrink-0" />
                )}
                <Icon className="size-4 text-muted-foreground" />
                <span>{meta.label}</span>
                <span className="text-xs text-muted-foreground font-normal">{items.length}</span>
              </CardTitle>
            </CardHeader>
            {isExpanded && (
              <CardContent className="space-y-1.5">
                {items.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center justify-between text-sm py-1 px-2 rounded hover:bg-muted/50 transition-colors group cursor-pointer"
                    onClick={() => viewChunks(s)}
                  >
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
            )}
          </Card>
        )
      })}

      {/* ── 知识源详情弹窗 ── */}
      <Dialog open={!!selected} onOpenChange={(open) => { if (!open) closeDetail() }}>
        <DialogContent className="max-w-7xl max-h-[92vh] overflow-y-auto w-[95vw]">
          <DialogHeader>
            <DialogTitle className="text-lg">
              {selected?.title || '知识源详情'}
            </DialogTitle>
            <DialogDescription>
              <div className="flex flex-wrap items-center gap-1.5 mt-1">
                {selected?.source_type && (
                  <Badge variant="secondary">{selected.source_type}</Badge>
                )}
                {selected?.para_category && (
                  <Badge variant="outline">{selected.para_category}</Badge>
                )}
                {selected?.knowledge_domain && (
                  <Badge variant="outline">{selected.knowledge_domain === 'platform' ? '平台研发' : '项目知识'}</Badge>
                )}
                {selected?.status && (
                  <Badge variant={selected.status === 'deprecated' ? 'destructive' : 'default'}>{selected.status}</Badge>
                )}
                {selected?.version && (
                  <Badge variant="outline" className="text-xs">v{selected.version}</Badge>
                )}
              </div>
            </DialogDescription>
          </DialogHeader>

          {/* 元数据摘要 */}
          {selected && (
            <div className="grid grid-cols-5 gap-3 text-sm bg-muted/30 rounded-lg p-4">
              <div>
                <span className="font-medium text-foreground">保鲜评分</span>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className={`inline-block size-2.5 rounded-full ${(selected.freshness_score ?? 1) >= 0.8 ? 'bg-green-500' : (selected.freshness_score ?? 1) >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'}`} />
                  <span className="text-base font-semibold">{((selected.freshness_score ?? 1) * 100).toFixed(0)}%</span>
                </div>
              </div>
              <div>
                <span className="font-medium text-foreground">最后验证</span>
                <div className="mt-1 text-sm">{selected.last_verified_at ? new Date(selected.last_verified_at).toLocaleDateString('zh-CN') : '未验证'}</div>
              </div>
              <div>
                <span className="font-medium text-foreground">创建时间</span>
                <div className="mt-1 text-sm">{selected.created_at?.slice(0, 10) || '—'}</div>
              </div>
              <div>
                <span className="font-medium text-foreground">更新时间</span>
                <div className="mt-1 text-sm">{selected.updated_at?.slice(0, 10) || '—'}</div>
              </div>
              <div>
                <span className="font-medium text-foreground">切片数</span>
                <div className="mt-1 text-sm">{chunks.length} 个</div>
              </div>
              {/* 知识溯源链路 */}
              <div className="col-span-5">
                <span className="font-medium text-foreground">溯源</span>
                <span className="ml-2 text-sm">
                  项目{selected.module_name ? ` → ${selected.module_name}` : ''} → {selected.source_ref || selected.source_type}
                </span>
              </div>
              {selected.source_ref && (
                <div className="col-span-5">
                  <span className="font-medium text-foreground">来源</span>
                  <span className="ml-2 text-sm break-all">{selected.source_ref}</span>
                </div>
              )}
              {selected.metadata_json && (
                <div className="col-span-5">
                  <span className="font-medium text-foreground block mb-1">元数据</span>
                  <pre className="text-xs whitespace-pre-wrap break-words bg-muted/50 rounded p-2 max-h-32 overflow-auto">
                    {(() => { try { return JSON.stringify(JSON.parse(selected.metadata_json), null, 2) } catch { return selected.metadata_json } })()}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* 原始内容（如果有） */}
          {selected?.raw_content && (
            <div className="space-y-2">
              <div className="text-sm font-medium text-foreground flex items-center gap-2">
                <span className="inline-block w-1 h-4 bg-primary rounded-full" />
                原始内容
              </div>
              <pre className="whitespace-pre-wrap break-words text-sm text-muted-foreground max-h-[500px] overflow-auto bg-muted/30 rounded-lg p-4 leading-relaxed border">
                {selected.raw_content}
              </pre>
            </div>
          )}

          {/* 切片列表 */}
          <div className="space-y-3">
            <div className="text-sm font-medium text-foreground flex items-center gap-2">
              <span className="inline-block w-1 h-4 bg-primary rounded-full" />
              切片列表 ({chunks.length})
            </div>
            {chunksLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="size-6 animate-spin text-muted-foreground" />
              </div>
            ) : chunks.length === 0 ? (
              <div className="text-sm text-muted-foreground py-8 text-center border rounded-lg border-dashed">
                该知识源暂无切片
              </div>
            ) : (
              <div className="grid gap-3">
                {chunks.map((c, idx) => (
                  <div key={c.id} className="rounded-lg border p-4 hover:border-primary/20 transition-colors">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="secondary">{c.chunk_type}</Badge>
                      <span className="text-sm font-medium">{c.title || `切片 #${idx + 1}`}</span>
                      <span className="ml-auto text-xs text-muted-foreground">
                        {c.token_count} tokens
                      </span>
                    </div>
                    <pre className="whitespace-pre-wrap break-words text-sm text-muted-foreground max-h-[50vh] overflow-auto bg-muted/40 rounded-md p-4 leading-relaxed">
                      {c.content}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
