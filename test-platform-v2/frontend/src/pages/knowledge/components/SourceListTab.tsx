import { useCallback, useEffect, useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
import { Loader2, CheckCircle2, RefreshCw, AlertCircle, Circle, CheckCheck } from '@/lib/icons'
import { toast } from 'sonner'

const TYPES = [
  { v: '_all', l: '全部类型' },
  { v: 'requirement', l: '需求' },
  { v: 'openapi', l: '接口导入' },
  { v: 'test_case', l: '接口用例' },
  { v: 'defect', l: '缺陷' },
  { v: 'execution', l: '执行失败' },
  { v: 'manual', l: '手动' },
]
const TYPE_LABEL: Record<string, string> = Object.fromEntries(TYPES.map((t) => [t.v, t.l]))
const PAGE_SIZE = 20

/** 判断是否今天内验证过 */
function isVerifiedToday(lastVerifiedAt: string | null | undefined): boolean {
  if (!lastVerifiedAt) return false
  const d = new Date(lastVerifiedAt)
  const now = new Date()
  return d.toDateString() === now.toDateString()
}

export default function SourceListTab() {
  const [rows, setRows] = useState<KnowledgeSource[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [type, setType] = useState('_all')
  const [loading, setLoading] = useState(true)

  const [selected, setSelected] = useState<KnowledgeSource | null>(null)
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    fetchKnowledgeSources({
      source_type: type === '_all' ? undefined : type,
      page,
      page_size: PAGE_SIZE,
    })
      .then((res) => {
        setRows(res.items)
        setTotal(res.total)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [type, page])

  useEffect(() => {
    load()
  }, [load])

  const [verifying, setVerifying] = useState<Set<number>>(new Set())

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

  const handleVerify = async (sourceId: number, e: React.MouseEvent) => {
    e.stopPropagation()
    setVerifying((prev) => new Set(prev).add(sourceId))
    try {
      const updated = await verifyKnowledgeSource(sourceId)
      // 即时更新本地行状态，不依赖全量 reload
      setRows((prev) =>
        prev.map((r) => (r.id === sourceId ? { ...r, ...updated } : r))
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

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Select
          value={type}
          onValueChange={(v) => {
            setType(v)
            setPage(1)
          }}
        >
          <SelectTrigger className="h-8 text-xs w-[140px]">
            <SelectValue placeholder="来源类型" />
          </SelectTrigger>
          <SelectContent>
            {TYPES.map((t) => (
              <SelectItem key={t.v} value={t.v}>
                {t.l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground">共 {total} 条</span>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[90px]">类型</TableHead>
              <TableHead>标题</TableHead>
              <TableHead className="w-[160px]">来源</TableHead>
              <TableHead className="w-[80px]">状态</TableHead>
              <TableHead className="w-[90px]">Wiki同步</TableHead>
              <TableHead className="w-[110px]">创建时间</TableHead>
              <TableHead className="w-[90px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center">
                  <Loader2 className="size-5 animate-spin text-muted-foreground inline" />
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-sm text-muted-foreground">
                  暂无知识源（上传需求 / 导入接口 / 新建用例后自动沉淀）
                </TableCell>
              </TableRow>
            ) : (
              rows.map((s) => (
                <TableRow key={s.id}>
                  <TableCell>
                    <Badge variant="secondary">{TYPE_LABEL[s.source_type] ?? s.source_type}</Badge>
                  </TableCell>
                  <TableCell className="max-w-[320px] truncate">{s.title}</TableCell>
                  <TableCell className="max-w-[160px] truncate text-xs text-muted-foreground">
                    {s.source_ref || '—'}
                  </TableCell>
                  <TableCell>
                    <Badge variant={s.status === 'deprecated' ? 'outline' : 'default'}>
                      {s.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <SyncBadge sourceId={s.id} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {s.created_at?.slice(0, 10)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-0.5">
                      <Button variant="ghost" size="sm" onClick={() => viewChunks(s)}>
                        查看
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        disabled={verifying.has(s.id) || isVerifiedToday(s.last_verified_at)}
                        onClick={(e) => handleVerify(s.id, e)}
                        title={isVerifiedToday(s.last_verified_at) ? '今日已验证' : '验证保鲜度'}
                      >
                        {verifying.has(s.id) ? (
                          <Loader2 className="size-3.5 animate-spin" />
                        ) : isVerifiedToday(s.last_verified_at) ? (
                          <CheckCheck className="size-3.5 text-green-600" />
                        ) : (
                          <CheckCircle2 className="size-3.5" />
                        )}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-end gap-2 text-xs">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          上一页
        </Button>
        <span className="text-muted-foreground">
          {page} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => setPage((p) => p + 1)}
        >
          下一页
        </Button>
      </div>

      {/* ── 知识源详情弹窗 ── */}
      <Dialog open={!!selected} onOpenChange={(open) => { if (!open) closeDetail() }}>
        <DialogContent className="max-w-7xl max-h-[90vh] overflow-y-auto w-[95vw]">
          <DialogHeader>
            <DialogTitle className="text-lg">
              {selected?.title || '知识源详情'}
            </DialogTitle>
            <DialogDescription>
              <div className="flex flex-wrap items-center gap-1.5 mt-1">
                {selected?.source_type && (
                  <Badge variant="secondary">{TYPE_LABEL[selected.source_type] ?? selected.source_type}</Badge>
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
                  项目{selected.module_name ? ` → ${selected.module_name}` : ''} → {selected.source_ref || selected.source_type} ({TYPE_LABEL[selected.source_type] ?? selected.source_type})
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

// ── Sync Status Badge (batch-30) ──

function SyncBadge({ sourceId }: { sourceId: number }) {
  // Simple placeholder - shows "未同步" for all sources
  // TODO: wire to GET /wiki/sync/bundle/{bundleId}/coverage
  const synced = false
  const partial = false
  const failed = false

  if (failed) {
    return (
      <Badge variant="outline" className="text-xs border-red-200 bg-red-50 text-red-700 gap-1">
        <AlertCircle className="h-3 w-3" />
        失败
      </Badge>
    )
  }
  if (synced) {
    return (
      <Badge variant="outline" className="text-xs border-green-200 bg-green-50 text-green-700 gap-1">
        <CheckCircle2 className="h-3 w-3" />
        已同步
      </Badge>
    )
  }
  if (partial) {
    return (
      <Badge variant="outline" className="text-xs border-yellow-200 bg-yellow-50 text-yellow-700 gap-1">
        <RefreshCw className="h-3 w-3" />
        部分
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="text-xs text-muted-foreground gap-1">
      <Circle className="h-3 w-3" />
      未同步
    </Badge>
  )
}
