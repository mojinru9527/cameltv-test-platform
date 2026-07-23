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

  // Batch approve/reject
  const [batchAction, setBatchAction] = useState<'approve' | 'reject' | null>(null)
  const [batchComment, setBatchComment] = useState('')
  const [batchLoading, setBatchLoading] = useState(false)

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

  const doBatchAction = async (action: 'approve' | 'reject', comment: string) => {
    if (selectedIds.size === 0) return
    setBatchLoading(true)
    let success = 0
    let failed = 0
    const fn = action === 'approve' ? approveArtifact : rejectArtifact
    for (const id of selectedIds) {
      try {
        const updated = await fn(id, comment)
        success++
        setRows((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
      } catch {
        failed++
      }
    }
    toast.success(`${action === 'approve' ? '批量采纳' : '批量驳回'}完成：成功 ${success} 条${failed > 0 ? `，失败 ${failed} 条` : ''}`)
    setSelectedIds(new Set())
    setBatchAction(null)
    setBatchComment('')
    setBatchLoading(false)
  }

  const handleBatchRejectClick = () => {
    setBatchAction('reject')
    setBatchComment('')
  }

  const pendingApproved = rows.filter((r) => r.review_status === 'approved')
  const pendingItemsCount = rows.filter((r) => r.review_status === 'pending').length
  const selectedPendingCount = rows.filter((r) => r.review_status === 'pending' && selectedIds.has(r.id)).length

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

        {/* 批量采纳（pending 选中） */}
        {selectedPendingCount > 0 && (
          <Button
            size="sm"
            variant="default"
            onClick={() => doBatchAction('approve', '')}
            disabled={batchLoading}
          >
            <CheckCircle2 className="size-4 mr-1" />
            {batchLoading && batchAction === 'approve' ? '采纳中…' : `批量采纳 (${selectedPendingCount})`}
          </Button>
        )}

        {/* 批量驳回（pending 选中） */}
        {selectedPendingCount > 0 && (
          <Button
            size="sm"
            variant="destructive"
            onClick={handleBatchRejectClick}
            disabled={batchLoading}
          >
            <XCircle className="size-4 mr-1" />
            {batchLoading && batchAction === 'reject' ? '驳回中…' : `批量驳回 (${selectedPendingCount})`}
          </Button>
        )}

        {/* 批量导入（approved 选中） */}
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
                    rows.filter((r) => r.review_status === 'pending' || r.review_status === 'approved').length > 0 &&
                    selectedIds.size === rows.filter((r) => r.review_status === 'pending' || r.review_status === 'approved').length
                  }
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedIds(new Set(
                        rows.filter((r) => r.review_status === 'pending' || r.review_status === 'approved').map((r) => r.id)
                      ))
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
                      {(isApproved || isPending) && (
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
            <Button variant="outline" size="sm" onClick={() => setDetailArtifact(null)}>关闭</Button>
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

      {/* Batch Reject Dialog */}
      <Dialog open={batchAction === 'reject'} onOpenChange={(open) => { if (!open) { setBatchAction(null); setBatchComment('') } }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>批量驳回 ({selectedPendingCount} 条)</DialogTitle>
            <DialogDescription>
              驳回后这些产物将不会被导入，可作为参考保留。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <Label>驳回原因（统一应用于所选条目）</Label>
            <Input
              placeholder="输入驳回原因…"
              value={batchComment}
              onChange={(e) => setBatchComment(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setBatchAction(null); setBatchComment('') }}>取消</Button>
            <Button
              variant="destructive"
              onClick={() => doBatchAction('reject', batchComment)}
              disabled={batchLoading}
            >
              {batchLoading ? '驳回中…' : '确认批量驳回'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
