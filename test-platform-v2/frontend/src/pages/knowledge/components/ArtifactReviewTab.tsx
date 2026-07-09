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
import { fetchAiArtifacts } from '@/api/knowledge'
import type { AiArtifact } from '@/types'
import { Loader2 } from '@/lib/icons'

const STATUSES = [
  { v: '_all', l: '全部状态' },
  { v: 'pending', l: '待审核' },
  { v: 'approved', l: '已采纳' },
  { v: 'rejected', l: '已驳回' },
  { v: 'imported', l: '已导入' },
]
const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pending: 'secondary',
  approved: 'default',
  rejected: 'destructive',
  imported: 'outline',
}
const PAGE_SIZE = 20

export default function ArtifactReviewTab() {
  const [rows, setRows] = useState<AiArtifact[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('_all')
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    fetchAiArtifacts({
      review_status: status === '_all' ? undefined : status,
      page,
      page_size: PAGE_SIZE,
    })
      .then((res) => {
        setRows(res.items)
        setTotal(res.total)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [status, page])

  useEffect(() => {
    load()
  }, [load])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v)
            setPage(1)
          }}
        >
          <SelectTrigger className="h-8 text-xs w-[140px]">
            <SelectValue placeholder="审核状态" />
          </SelectTrigger>
          <SelectContent>
            {STATUSES.map((s) => (
              <SelectItem key={s.v} value={s.v}>
                {s.l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground">共 {total} 条</span>
        <span className="ml-auto text-xs text-muted-foreground">
          采纳 / 驳回 / 批量导入将在 M4 开放
        </span>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[110px]">类型</TableHead>
              <TableHead>标题</TableHead>
              <TableHead className="w-[80px]">置信度</TableHead>
              <TableHead className="w-[90px]">审核状态</TableHead>
              <TableHead className="w-[110px]">创建时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center">
                  <Loader2 className="size-5 animate-spin text-muted-foreground inline" />
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-sm text-muted-foreground">
                  暂无 AI 产物（Agent 生成能力将在 M4 上线，生成结果会进入此审核台）
                </TableCell>
              </TableRow>
            ) : (
              rows.map((a) => (
                <TableRow key={a.id}>
                  <TableCell>
                    <Badge variant="secondary">{a.artifact_type}</Badge>
                  </TableCell>
                  <TableCell className="max-w-[360px] truncate">{a.title}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {(a.confidence * 100).toFixed(0)}%
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANT[a.review_status] ?? 'secondary'}>
                      {a.review_status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {a.created_at?.slice(0, 10)}
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
    </div>
  )
}
