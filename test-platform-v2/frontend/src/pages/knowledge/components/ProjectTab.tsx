import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { fetchKnowledgeSources, fetchSourceChunks } from '@/api/knowledge'
import type { KnowledgeChunk, KnowledgeSource } from '@/types'
import { Loader2, FolderOpen } from '@/lib/icons'

function freshnessBadge(score: number): { color: string; label: string } {
  if (score >= 0.8) return { color: 'bg-green-100 text-green-700', label: '新鲜' }
  if (score >= 0.4) return { color: 'bg-yellow-100 text-yellow-700', label: '待关注' }
  return { color: 'bg-red-100 text-red-700', label: '过期' }
}

export default function ProjectTab() {
  const [sources, setSources] = useState<KnowledgeSource[]>([])
  const [loading, setLoading] = useState(true)

  // ── 详情弹窗状态 ──
  const [selected, setSelected] = useState<KnowledgeSource | null>(null)
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchKnowledgeSources({ para_category: 'project', page_size: 100 })
      .then((page) => { if (!cancelled) setSources(page.items) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

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
                <div
                  key={s.id}
                  className="flex items-center justify-between text-sm py-1 px-2 rounded hover:bg-muted/50 transition-colors cursor-pointer"
                  onClick={() => viewChunks(s)}
                >
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

      {/* ── 知识源详情弹窗 ── */}
      <Dialog open={!!selected} onOpenChange={(open) => { if (!open) closeDetail() }}>
        <DialogContent className="max-w-7xl max-h-[94vh] overflow-y-auto w-[95vw]">
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
                    <pre className="whitespace-pre-wrap break-words text-sm text-muted-foreground max-h-[600px] overflow-auto bg-muted/40 rounded-md p-4 leading-relaxed">
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
