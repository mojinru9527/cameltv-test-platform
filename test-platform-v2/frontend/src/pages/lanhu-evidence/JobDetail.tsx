import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth'
import {
  fetchLanhuEvidenceJob,
  fetchLanhuEvidencePages,
  fetchLanhuEvidenceAssets,
  reviewLanhuEvidencePage,
  importLanhuEvidence,
  cancelLanhuEvidenceJob,
  retryLanhuEvidenceJob,
  type LanhuEvidencePage,
  type LanhuEvidenceQuality,
} from '@/api/lanhuEvidence'
import { Button, Badge, Label } from '@/ui'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import PageHeader from '@/components/PageHeader'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  ArrowLeft,
  Eye,
  CheckCircle2,
  XCircle,
  Download,
  RotateCcw,
  Loader2,
} from '@/lib/icons'
import {
  jobStatusLabel,
  jobStatusTone,
  stageLabel,
  pageCaptureLabel,
  pageOcrLabel,
  reviewStatusLabel,
} from './labels'

function parseQuality(raw: string): LanhuEvidenceQuality {
  try {
    return JSON.parse(raw || '{}') as LanhuEvidenceQuality
  } catch {
    return {}
  }
}

export default function LanhuEvidenceJobDetail() {
  useDocumentTitle('证据包任务详情')
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const jobId = Number(id)
  const canReview = useAuthStore((state) => state.hasPerm)('lanhu_evidence:review')
  const canImport = useAuthStore((state) => state.hasPerm)('lanhu_evidence:import')
  const canRun = useAuthStore((state) => state.hasPerm)('lanhu_evidence:run')

  const { data: job, isLoading, isError, error, refetch } = useApi(
    (signal) => fetchLanhuEvidenceJob(jobId, signal),
    [jobId],
  )
  const { data: pagesData, isLoading: pagesLoading, refetch: refetchPages } = useApi(
    (signal) => fetchLanhuEvidencePages(jobId, signal),
    [jobId],
  )
  const { data: assets } = useApi(
    (signal) => fetchLanhuEvidenceAssets(jobId, signal),
    [jobId],
  )

  const [detailPage, setDetailPage] = useState<LanhuEvidencePage | null>(null)
  const [reviewTarget, setReviewTarget] = useState<LanhuEvidencePage | null>(null)
  const [reviewApproved, setReviewApproved] = useState(true)
  const [reviewComment, setReviewComment] = useState('')
  const [reviewing, setReviewing] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [importTargets, setImportTargets] = useState({
    import_to_requirement: true,
    import_to_knowledge: true,
    import_to_wiki: true,
  })
  const [importing, setImporting] = useState(false)

  const pages = pagesData?.items || []
  const quality = job ? parseQuality(job.quality_json) : {}
  const pageAssets = assets || []

  const screenshotFor = (page: LanhuEvidencePage) =>
    pageAssets.find((a) => a.page_id === page.id && a.asset_type === 'screenshot')

  const handleReview = async () => {
    if (!reviewTarget) return
    if (!reviewApproved && !reviewComment.trim()) {
      toast.error('驳回时请填写原因')
      return
    }
    setReviewing(true)
    try {
      await reviewLanhuEvidencePage(reviewTarget.id, {
        approved: reviewApproved,
        comment: reviewComment.trim() || (reviewApproved ? '人工审核通过' : ''),
      })
      toast.success(reviewApproved ? '页面已通过' : '页面已驳回')
      setReviewTarget(null)
      refetchPages()
      refetch()
    } catch {
      // handled by interceptor
    } finally {
      setReviewing(false)
    }
  }

  const handleImport = async () => {
    if (!job) return
    setImporting(true)
    try {
      await importLanhuEvidence(job.id, importTargets)
      toast.success('导入完成')
      setImportOpen(false)
      refetch()
    } catch {
      // handled by interceptor
    } finally {
      setImporting(false)
    }
  }

  const handleCancel = async () => {
    if (!job) return
    try {
      await cancelLanhuEvidenceJob(job.id)
      toast.success('已请求取消')
      refetch()
    } catch {
      // handled by interceptor
    }
  }

  const handleRetry = async () => {
    if (!job) return
    try {
      await retryLanhuEvidenceJob(job.id)
      toast.success('已创建重试任务')
      refetch()
    } catch {
      // handled by interceptor
    }
  }

  const canImportNow = canImport && job?.status === 'success' && quality.import_ready

  return (
    <div>
      <PageHeader title={`证据包任务 #${jobId}`} description={job?.source_url || ' '}>
        <Button size="sm" variant="secondary" className="min-h-11" onClick={() => navigate('/lanhu-evidence')} data-icon="inline-start">
          <ArrowLeft />
          返回列表
        </Button>
      </PageHeader>

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={job}
        onRetry={refetch}
        loadingVariant="skeleton"
        skeletonType="card"
      >
        {(current) => (
          <>
            {/* ── 摘要卡 ── */}
            <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border bg-card p-4">
                <div className="text-xs text-muted-foreground">状态</div>
                <div className="mt-1 flex items-center gap-2">
                  <Badge tone={jobStatusTone(current.status)}>{jobStatusLabel(current.status)}</Badge>
                  <span className="text-sm text-muted-foreground">{stageLabel(current.stage)}</span>
                </div>
              </div>
              <div className="rounded-xl border bg-card p-4">
                <div className="text-xs text-muted-foreground">页面</div>
                <div className="mt-1 text-lg font-semibold">
                  {current.captured_pages}/{current.total_pages}
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    OCR {current.ocr_pages} · 失败 {current.failed_pages}
                  </span>
                </div>
              </div>
              <div className="rounded-xl border bg-card p-4">
                <div className="text-xs text-muted-foreground">质量门禁</div>
                <div className="mt-1">
                  <Badge tone={quality.import_ready ? 'success' : 'neutral'}>
                    {quality.import_ready ? '可导入' : '未达标'}
                  </Badge>
                </div>
              </div>
              <div className="rounded-xl border bg-card p-4">
                <div className="text-xs text-muted-foreground">操作</div>
                <div className="mt-1 flex flex-wrap items-center gap-1">
                  {canImportNow && (
                    <Button size="sm" className="min-h-9" onClick={() => setImportOpen(true)} data-icon="inline-start">
                      <Download />
                      导入
                    </Button>
                  )}
                  {canRun && (current.status === 'pending' || current.status === 'running') && (
                    <Button size="sm" variant="secondary" className="min-h-9" onClick={handleCancel}>
                      取消
                    </Button>
                  )}
                  {canRun && current.status === 'failed' && (
                    <Button size="sm" variant="secondary" className="min-h-9" onClick={handleRetry} data-icon="inline-start">
                      <RotateCcw />
                      重试
                    </Button>
                  )}
                </div>
              </div>
            </div>

            {current.error_message && (
              <div className="mt-3 rounded-lg border border-status-danger/40 bg-status-danger-muted p-3 text-sm text-status-danger">
                错误：{current.error_message}
              </div>
            )}

            {/* ── 页面表 ── */}
            <div className="mt-6">
              <AsyncState
                isLoading={pagesLoading}
                isError={false}
                error={null}
                data={pages.length > 0 ? pages : undefined}
                emptyTitle="暂无页面"
                emptyDescription="任务完成后将展示采集到的设计页面"
                loadingVariant="skeleton"
                skeletonType="table"
                loadingRows={5}
              >
                {(items) => (
                  <div className="rounded-xl border bg-card">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-12">#</TableHead>
                          <TableHead>页面名称</TableHead>
                          <TableHead>文件夹</TableHead>
                          <TableHead>捕获</TableHead>
                          <TableHead>OCR</TableHead>
                          <TableHead>审核</TableHead>
                          <TableHead className="w-[130px]">操作</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {items.map((page) => (
                          <TableRow key={page.id}>
                            <TableCell className="text-xs text-muted-foreground">{page.order_index + 1}</TableCell>
                            <TableCell className="max-w-[260px]">
                              <span className="truncate font-medium" title={page.page_name}>{page.page_name || '（未命名）'}</span>
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground">{page.folder || '—'}</TableCell>
                            <TableCell>
                              <Badge tone={page.capture_status === 'success' ? 'success' : page.capture_status === 'failed' ? 'danger' : 'neutral'}>
                                {pageCaptureLabel(page.capture_status)}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge tone={page.ocr_status === 'success' ? 'success' : page.ocr_status === 'unavailable' ? 'warning' : 'neutral'}>
                                {pageOcrLabel(page.ocr_status)}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge tone={page.review_status === 'approved' ? 'success' : page.review_status === 'rejected' ? 'danger' : 'neutral'}>
                                {reviewStatusLabel(page.review_status)}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <Button size="sm" variant="ghost" aria-label={`查看页面 ${page.page_name}`} onClick={() => setDetailPage(page)}>
                                  <Eye className="size-4" />
                                </Button>
                                {canReview && page.capture_status === 'success' && page.review_status !== 'approved' && (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    aria-label={`审核页面 ${page.page_name}`}
                                    onClick={() => {
                                      setReviewTarget(page)
                                      setReviewApproved(true)
                                      setReviewComment('')
                                    }}
                                  >
                                    <CheckCircle2 className="size-4" />
                                  </Button>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </AsyncState>
            </div>
          </>
        )}
      </AsyncState>

      {/* ── 页面详情 Dialog ── */}
      <Dialog open={detailPage !== null} onOpenChange={(open) => { if (!open) setDetailPage(null) }}>
        <DialogContent className="sm:max-w-5xl w-[95vw] max-h-[92vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{detailPage?.page_name || '页面详情'}</DialogTitle>
            <DialogDescription>
              {detailPage?.page_path || ' '} · 捕获 {detailPage ? pageCaptureLabel(detailPage.capture_status) : ''} · OCR{' '}
              {detailPage ? pageOcrLabel(detailPage.ocr_status) : ''}
            </DialogDescription>
          </DialogHeader>
          {detailPage && (
            <div className="grid gap-4 md:grid-cols-2">
              {screenshotFor(detailPage) && (
                <div className="rounded-lg border bg-muted p-2">
                  <img
                    src={`/api/v1/lanhu-evidence/assets/${screenshotFor(detailPage)!.id}`}
                    alt={`页面 ${detailPage.page_name} 截图`}
                    className="max-h-[70vh] w-full object-contain"
                  />
                </div>
              )}
              <pre className="max-h-[50vh] overflow-y-auto whitespace-pre-wrap rounded-lg border bg-muted p-3 text-xs leading-relaxed">
                {detailPage.merged_text || '（无文本内容）'}
              </pre>
            </div>
          )}
          <DialogFooter>
            <Button variant="secondary" onClick={() => setDetailPage(null)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── 审核 Dialog ── */}
      <Dialog open={reviewTarget !== null} onOpenChange={(open) => { if (!open) setReviewTarget(null) }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>审核页面</DialogTitle>
            <DialogDescription>
              {reviewTarget?.page_name || ''}（{reviewTarget ? pageOcrLabel(reviewTarget.ocr_status) : ''}）
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-2">
            <div className="flex gap-2">
              <Button
                variant={reviewApproved ? 'primary' : 'secondary'}
                className="flex-1"
                onClick={() => setReviewApproved(true)}
                data-icon="inline-start"
              >
                <CheckCircle2 />
                通过（豁免无 OCR）
              </Button>
              <Button
                variant={reviewApproved ? 'secondary' : 'danger'}
                className="flex-1"
                onClick={() => setReviewApproved(false)}
                data-icon="inline-start"
              >
                <XCircle />
                驳回
              </Button>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="review-comment">原因 / 备注</Label>
              <Textarea
                id="review-comment"
                rows={3}
                placeholder={reviewApproved ? '可留空，默认「人工审核通过」' : '驳回时必填，说明缺什么'}
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setReviewTarget(null)}>
              取消
            </Button>
            <Button disabled={reviewing} onClick={handleReview} data-icon="inline-start">
              {reviewing && <Loader2 className="animate-spin" />}
              提交
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── 导入 Dialog ── */}
      <Dialog open={importOpen} onOpenChange={(open) => { if (!open) setImportOpen(false) }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>导入证据包</DialogTitle>
            <DialogDescription>将本任务全部页面文本导入所选目标</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2 rounded-lg border p-3">
            {([
              ['import_to_requirement', '需求文档'],
              ['import_to_knowledge', '知识库（RAG）'],
              ['import_to_wiki', 'Wiki'],
            ] as const).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm cursor-pointer">
                <Checkbox
                  checked={importTargets[key]}
                  onCheckedChange={(v) =>
                    setImportTargets((prev) => ({ ...prev, [key]: Boolean(v) }))
                  }
                />
                {label}
              </label>
            ))}
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setImportOpen(false)}>
              取消
            </Button>
            <Button disabled={importing} onClick={handleImport} data-icon="inline-start">
              {importing && <Loader2 className="animate-spin" />}
              开始导入
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
