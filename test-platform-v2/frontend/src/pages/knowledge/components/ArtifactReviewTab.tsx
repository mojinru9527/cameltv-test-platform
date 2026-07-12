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
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { fetchAiArtifacts, approveArtifact, rejectArtifact, importArtifact } from '@/api/knowledge'
import type { AiArtifact } from '@/types'
import { Loader2, CheckCircle2, XCircle, Download, Eye } from '@/lib/icons'

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
const TYPE_LABELS: Record<string, string> = {
  test_case: '测试用例',
  requirement_analysis: '需求分析',
  impact_analysis: '影响分析',
  failure_analysis: '失败分析',
}
const PAGE_SIZE = 20

export default function ArtifactReviewTab() {
  const [rows, setRows] = useState<AiArtifact[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('_all')
  const [loading, setLoading] = useState(true)

  // Detail dialog
  const [detailArtifact, setDetailArtifact] = useState<AiArtifact | null>(null)

  // Approve/reject dialog
  const [actionTarget, setActionTarget] = useState<{ id: number; action: 'approve' | 'reject' } | null>(null)
  const [actionComment, setActionComment] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  // Batch import
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [importing, setImporting] = useState(false)

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
      .catch(() => toast.error('加载产物列表失败'))
      .finally(() => setLoading(false))
  }, [status, page])

  useEffect(() => {
    load()
  }, [load])

  const handleApproveOrReject = async () => {
    if (!actionTarget) return
    setActionLoading(true)
    try {
      const fn = actionTarget.action === 'approve' ? approveArtifact : rejectArtifact
      const updated = await fn(actionTarget.id, actionComment)
      setRows((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
      toast.success(actionTarget.action === 'approve' ? '已采纳' : '已驳回')
      setActionTarget(null)
      setActionComment('')
    } catch (e: any) {
      toast.error(e?.message || '操作失败')
    } finally {
      setActionLoading(false)
    }
  }

  const handleBatchImport = async () => {
    if (selectedIds.size === 0) return
    setImporting(true)
    let success = 0
    let failed = 0
    for (const id of selectedIds) {
      try {
        await importArtifact(id)
        success++
        setRows((prev) =>
          prev.map((r) => (r.id === id ? { ...r, review_status: 'imported' } : r))
        )
      } catch {
        failed++
      }
    }
    toast.success(`导入完成：成功 ${success} 条${failed > 0 ? `，失败 ${failed} 条` : ''}`)
    setSelectedIds(new Set())
    setImporting(false)
  }

  const pendingApproved = rows.filter((r) => r.review_status === 'approved')

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
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

        {pendingApproved.length > 0 && (
          <Button
            size="sm"
            variant="outline"
            className="ml-auto"
            onClick={handleBatchImport}
            disabled={importing}
          >
            <Download className="size-4 mr-1" />
            {importing ? '导入中…' : `批量导入 (${selectedIds.size || pendingApproved.length})`}
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={
                    pendingApproved.length > 0 &&
                    selectedIds.size === pendingApproved.length
                  }
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedIds(new Set(pendingApproved.map((r) => r.id)))
                    } else {
                      setSelectedIds(new Set())
                    }
                  }}
                  aria-label="Select all"
                />
              </TableHead>
              <TableHead className="w-[110px]">类型</TableHead>
              <TableHead>标题</TableHead>
              <TableHead className="w-[80px]">置信度</TableHead>
              <TableHead className="w-[90px]">审核状态</TableHead>
              <TableHead className="w-[140px]">操作</TableHead>
              <TableHead className="w-[110px]">创建时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center">
                  <Loader2 className="size-5 animate-spin text-muted-foreground inline" />
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center text-sm text-muted-foreground">
                  暂无 AI 产物
                </TableCell>
              </TableRow>
            ) : (
              rows.map((a) => {
                const isApproved = a.review_status === 'approved'
                const isPending = a.review_status === 'pending'
                return (
                  <TableRow key={a.id}>
                    <TableCell>
                      {isApproved && (
                        <Checkbox
                          checked={selectedIds.has(a.id)}
                          onCheckedChange={(checked) => {
                            setSelectedIds((prev) => {
                              const next = new Set(prev)
                              if (checked) next.add(a.id)
                              else next.delete(a.id)
                              return next
                            })
                          }}
                          aria-label={`Select artifact ${a.id}`}
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        {TYPE_LABELS[a.artifact_type] || a.artifact_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate">{a.title}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {(a.confidence * 100).toFixed(0)}%
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[a.review_status] ?? 'secondary'}>
                        {a.review_status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          onClick={() => setDetailArtifact(a)}
                          title="查看详情"
                        >
                          <Eye className="size-4" />
                        </Button>
                        {isPending && (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-8 text-green-600 hover:text-green-700"
                              onClick={() => setActionTarget({ id: a.id, action: 'approve' })}
                              title="采纳"
                            >
                              <CheckCircle2 className="size-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-8 text-red-600 hover:text-red-700"
                              onClick={() => setActionTarget({ id: a.id, action: 'reject' })}
                              title="驳回"
                            >
                              <XCircle className="size-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {a.created_at?.slice(0, 10)}
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
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

      {/* Detail Dialog */}
      <Dialog open={!!detailArtifact} onOpenChange={(open) => { if (!open) setDetailArtifact(null) }}>
        <DialogContent className="max-w-xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-sm">{detailArtifact?.title}</DialogTitle>
            <DialogDescription className="text-xs">
              {TYPE_LABELS[detailArtifact?.artifact_type || ''] || detailArtifact?.artifact_type}
              {' · '}置信度 {((detailArtifact?.confidence ?? 0) * 100).toFixed(0)}%
            </DialogDescription>
          </DialogHeader>
          <div className="text-xs">
            <pre className="bg-muted p-3 rounded-md overflow-x-auto whitespace-pre-wrap max-h-96">
              {(() => {
                try {
                  return JSON.stringify(JSON.parse(detailArtifact?.content_json || '{}'), null, 2)
                } catch {
                  return detailArtifact?.content_json || '(无内容)'
                }
              })()}
            </pre>
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDetailArtifact(null)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Approve/Reject Dialog */}
      <Dialog open={!!actionTarget} onOpenChange={(open) => { if (!open) setActionTarget(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionTarget?.action === 'approve' ? '采纳 AI 产物' : '驳回 AI 产物'}
            </DialogTitle>
            <DialogDescription>
              {actionTarget?.action === 'approve'
                ? '采纳后该产物可被导入到正式用例库。'
                : '驳回后该产物将不会被导入，可作为参考保留。'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <Label>审核意见（可选）</Label>
            <Input
              placeholder="输入审核意见…"
              value={actionComment}
              onChange={(e) => setActionComment(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setActionTarget(null)}>取消</Button>
            <Button
              variant={actionTarget?.action === 'approve' ? 'default' : 'destructive'}
              onClick={handleApproveOrReject}
              disabled={actionLoading}
            >
              {actionLoading
                ? '处理中…'
                : actionTarget?.action === 'approve'
                ? '确认采纳'
                : '确认驳回'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
