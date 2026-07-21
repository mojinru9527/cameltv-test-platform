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
import { Loader2, CheckCircle2 } from '@/lib/icons'
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
      await verifyKnowledgeSource(sourceId)
      toast.success('已验证')
      load()
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
                        disabled={verifying.has(s.id)}
                        onClick={(e) => handleVerify(s.id, e)}
                        title="验证保鲜度"
                      >
                        <CheckCircle2 className="size-3.5" />
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
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-base">
              切片详情 · {selected?.title}
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
              </div>
            </DialogDescription>
          </DialogHeader>

          {/* 元数据摘要 */}
          {selected && (
            <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground bg-muted/30 rounded-lg p-3">
              <div>
                <span className="font-medium text-foreground">保鲜评分</span>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className={`inline-block size-2 rounded-full ${(selected.freshness_score ?? 1) >= 0.8 ? 'bg-green-500' : (selected.freshness_score ?? 1) >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'}`} />
                  <span>{((selected.freshness_score ?? 1) * 100).toFixed(0)}%</span>
                </div>
              </div>
              <div>
                <span className="font-medium text-foreground">最后验证</span>
                <div className="mt-0.5">{selected.last_verified_at ? new Date(selected.last_verified_at).toLocaleDateString('zh-CN') : '未验证'}</div>
              </div>
              <div>
                <span className="font-medium text-foreground">创建时间</span>
                <div className="mt-0.5">{selected.created_at?.slice(0, 10) || '—'}</div>
              </div>
              {selected.version && (
                <div className="col-span-3">
                  <span className="font-medium text-foreground">版本</span>
                  <span className="ml-1">{selected.version}</span>
                </div>
              )}
              {selected.source_ref && (
                <div className="col-span-3">
                  <span className="font-medium text-foreground">来源</span>
                  <span className="ml-1">{selected.source_ref}</span>
                </div>
              )}
            </div>
          )}

          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">
              切片列表 ({chunks.length})
            </div>
            {chunksLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="size-5 animate-spin text-muted-foreground" />
              </div>
            ) : chunks.length === 0 ? (
              <div className="text-sm text-muted-foreground py-4 text-center">该知识源暂无切片</div>
            ) : (
              chunks.map((c) => (
                <div key={c.id} className="rounded-md border p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <Badge variant="secondary">{c.chunk_type}</Badge>
                    <span className="text-xs font-medium">{c.title}</span>
                    <span className="ml-auto text-xs text-muted-foreground">
                      {c.token_count} tokens
                    </span>
                  </div>
                  <pre className="whitespace-pre-wrap break-words text-xs text-muted-foreground max-h-48 overflow-auto bg-muted/50 rounded p-2">
                    {c.content}
                  </pre>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
