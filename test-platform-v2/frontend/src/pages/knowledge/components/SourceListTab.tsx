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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchKnowledgeSources, fetchSourceChunks } from '@/api/knowledge'
import type { KnowledgeChunk, KnowledgeSource } from '@/types'
import { Loader2 } from '@/lib/icons'

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

  const viewChunks = (src: KnowledgeSource) => {
    setSelected(src)
    setChunksLoading(true)
    fetchSourceChunks(src.id)
      .then(setChunks)
      .catch(() => setChunks([]))
      .finally(() => setChunksLoading(false))
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
                    <Button variant="ghost" size="sm" onClick={() => viewChunks(s)}>
                      查看切片
                    </Button>
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

      {selected && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              切片 · {selected.title}
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                （embedding 将在 M2 生成）
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {chunksLoading ? (
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            ) : chunks.length === 0 ? (
              <div className="text-sm text-muted-foreground">该知识源暂无切片</div>
            ) : (
              chunks.map((c) => (
                <div key={c.id} className="rounded-md border p-2">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="secondary">{c.chunk_type}</Badge>
                    <span className="text-xs font-medium">{c.title}</span>
                    <span className="ml-auto text-xs text-muted-foreground">
                      {c.token_count} tokens
                    </span>
                  </div>
                  <pre className="whitespace-pre-wrap break-words text-xs text-muted-foreground max-h-40 overflow-auto">
                    {c.content}
                  </pre>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
