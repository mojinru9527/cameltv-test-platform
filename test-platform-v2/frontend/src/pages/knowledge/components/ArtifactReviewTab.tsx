import { useEffect, useState } from 'react'
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
import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/ui'
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
const STATUS_TONE: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  pending: 'neutral',
  approved: 'success',
  rejected: 'danger',
  imported: 'info',
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

  const [importingId, setImportingId] = useState<number | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    fetchAiArtifacts({
      review_status: status === '_all' ? undefined : status,
      page,
      page_size: PAGE_SIZE,
    }, controller.signal)
      .then((res) => {
        if (controller.signal.aborted) return
        setRows(res.items)
        setTotal(res.total)
      })
      .catch((loadError: unknown) => {
        if (controller.signal.aborted) return
        toast.error(loadError instanceof Error ? loadError.message : '加载产物列表失败')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [status, page])

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

  const handleImport = async (id: number) => {
    setImportingId(id)
    try {
      await importArtifact(id)
      setRows((prev) =>
        prev.map((r) => (r.id === id ? { ...r, review_status: 'imported' } : r))
      )
      toast.success('已导入产物')
    } catch (importError: any) {
      toast.error(importError?.message || '导入失败')
    } finally {
      setImportingId(null)
    }
  }

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

      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
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
                <TableCell colSpan={6} className="p-3" aria-label="正在加载 AI 产物">
                  <div className="space-y-2" aria-hidden="true">
                    {Array.from({ length: 4 }, (_, index) => (
                      <Skeleton key={index} className="h-8 w-full" />
                    ))}
                  </div>
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-sm text-muted-foreground">
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
                      <Badge tone="neutral">
                        {TYPE_LABELS[a.artifact_type] || a.artifact_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate">{a.title}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {(a.confidence * 100).toFixed(0)}%
                    </TableCell>
                    <TableCell>
                      <Badge tone={STATUS_TONE[a.review_status] ?? 'neutral'}>
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
                          aria-label={`查看制品 ${a.title || a.id} 详情`}
                        >
                          <Eye className="size-4" />
                        </Button>
                        {isPending && (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-8 text-status-success hover:text-status-success"
                              onClick={() => setActionTarget({ id: a.id, action: 'approve' })}
                              aria-label={`采纳制品 ${a.title || a.id}`}
                            >
                              <CheckCircle2 className="size-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-8 text-status-danger hover:text-status-danger"
                              onClick={() => setActionTarget({ id: a.id, action: 'reject' })}
                              aria-label={`驳回制品 ${a.title || a.id}`}
                            >
                              <XCircle className="size-4" />
                            </Button>
                          </>
                        )}
                        {isApproved && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8"
                            onClick={() => handleImport(a.id)}
                            disabled={importingId === a.id}
                            aria-label={`导入制品 ${a.title || a.id}`}
                          >
                            {importingId === a.id
                              ? <Loader2 className="size-4 animate-spin" />
                              : <Download className="size-4" />}
                          </Button>
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
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          上一页
        </Button>
        <span className="text-muted-foreground">
          {page} / {totalPages}
        </span>
        <Button
          variant="secondary"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => setPage((p) => p + 1)}
        >
          下一页
        </Button>
      </div>

      {/* Detail Dialog */}
      <Dialog open={!!detailArtifact} onOpenChange={(open) => { if (!open) setDetailArtifact(null) }}>
        <DialogContent className="max-w-7xl max-h-[94vh] overflow-y-auto w-[95vw]">
          <DialogHeader>
            <DialogTitle className="text-sm">{detailArtifact?.title}</DialogTitle>
            <DialogDescription className="text-xs">
              {TYPE_LABELS[detailArtifact?.artifact_type || ''] || detailArtifact?.artifact_type}
              {' · '}置信度 {((detailArtifact?.confidence ?? 0) * 100).toFixed(0)}%
            </DialogDescription>
          </DialogHeader>
          <div className="text-xs">
            <pre className="bg-muted p-3 rounded-md overflow-x-auto whitespace-pre-wrap break-words max-h-[600px]">
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
            <Button variant="secondary" size="sm" onClick={() => setDetailArtifact(null)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Approve/Reject Dialog */}
      <Dialog open={!!actionTarget} onOpenChange={(open) => { if (!open) setActionTarget(null) }}>
        <DialogContent className="max-w-md">
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
            <Button variant="secondary" onClick={() => setActionTarget(null)}>取消</Button>
            <Button
              variant={actionTarget?.action === 'approve' ? 'primary' : 'danger'}
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
