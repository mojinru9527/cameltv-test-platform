import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
  Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import {
  cancelLanhuEvidenceJob,
  deleteLanhuEvidenceJob,
  downloadLanhuEvidenceAsset,
  fetchLanhuEvidenceAssets,
  fetchLanhuEvidenceJob,
  fetchLanhuEvidencePages,
  importLanhuEvidence,
  reviewLanhuEvidencePage,
  retryLanhuEvidenceJob,
} from '@/api/lanhuEvidence'
import type {
  LanhuEvidenceAsset,
  LanhuEvidenceJob,
  LanhuEvidencePage,
  LanhuEvidenceQuality,
} from '@/api/lanhuEvidence'
import { Loader2, RefreshCw } from '@/lib/icons'
import { useAuthStore } from '@/stores/auth'

interface Props {
  open: boolean
  onOpenChange: (v: boolean) => void
  jobId: number | null
}

const STATUS_VARIANT: Record<string, string> = {
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  success_with_warnings: 'bg-amber-50 text-amber-700 border-amber-200',
  running: 'bg-blue-50 text-blue-700 border-blue-200',
  pending: 'bg-slate-50 text-slate-600 border-slate-200',
  failed: 'bg-red-50 text-red-700 border-red-200',
  cancelled: 'bg-slate-50 text-slate-500 border-slate-200',
}

function parseQuality(job: LanhuEvidenceJob | null): LanhuEvidenceQuality {
  if (!job?.quality_json) return {}
  try {
    return JSON.parse(job.quality_json)
  } catch {
    return {}
  }
}

function parseJsonObject(value?: string): Record<string, unknown> {
  if (!value) return {}
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function formatPageNumbers(indexes?: number[]): string {
  return (indexes || []).map((index) => `第 ${index + 1} 页`).join('、')
}

function assetDownloadName(asset: LanhuEvidenceAsset): string {
  const name = asset.relative_path.split(/[\\/]/).pop()
  if (name) return name
  if (asset.asset_type === 'word') return `lanhu-evidence-${asset.job_id}.docx`
  if (asset.asset_type === 'json') return `lanhu-evidence-${asset.job_id}.json`
  return `lanhu-evidence-asset-${asset.id}`
}

/** 证据包任务详情抽屉 —— 状态 / 计数 / 质量 / 页面列表 / 重试·取消。 */
export default function LanhuEvidenceJobDrawer({ open, onOpenChange, jobId }: Props) {
  const hasPerm = useAuthStore((state) => state.hasPerm)
  const [displayJobId, setDisplayJobId] = useState<number | null>(jobId)
  const [job, setJob] = useState<LanhuEvidenceJob | null>(null)
  const [pages, setPages] = useState<LanhuEvidencePage[]>([])
  const [assets, setAssets] = useState<LanhuEvidenceAsset[]>([])
  const [loading, setLoading] = useState(false)
  const [reviewPage, setReviewPage] = useState<LanhuEvidencePage | null>(null)
  const [reviewComment, setReviewComment] = useState('')
  const [reviewing, setReviewing] = useState(false)
  const [importing, setImporting] = useState(false)
  const [downloadingAssetId, setDownloadingAssetId] = useState<number | null>(null)

  const loadJob = useCallback(async (targetJobId: number) => {
    setLoading(true)
    try {
      const [j, p, a] = await Promise.all([
        fetchLanhuEvidenceJob(targetJobId),
        fetchLanhuEvidencePages(targetJobId),
        fetchLanhuEvidenceAssets(targetJobId),
      ])
      setJob(j)
      setPages(p.items)
      setAssets(a)
    } catch (e: any) {
      toast.error(e?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const load = useCallback(async () => {
    if (displayJobId) await loadJob(displayJobId)
  }, [displayJobId, loadJob])

  useEffect(() => {
    if (open && jobId) {
      setDisplayJobId(jobId)
      void loadJob(jobId)
    }
  }, [open, jobId, loadJob])

  const quality = parseQuality(job)
  const requestedOptions = parseJsonObject(job?.requested_options_json)
  const importResult = parseJsonObject(job?.import_result_json)
  const requestedImport = {
    import_to_requirement: requestedOptions.import_to_requirement === true,
    import_to_knowledge: requestedOptions.import_to_knowledge === true,
    import_to_wiki: requestedOptions.import_to_wiki === true,
  }
  const hasRequestedImport = Object.values(requestedImport).some(Boolean)
  const importCompleted = Object.keys(importResult).length > 0 && !importResult.error
  const exportAssets = assets.filter((asset) => asset.asset_type === 'word' || asset.asset_type === 'json')

  const onReview = async () => {
    if (!reviewPage || reviewComment.trim().length < 3) return
    setReviewing(true)
    try {
      await reviewLanhuEvidencePage(reviewPage.id, {
        approved: true,
        comment: reviewComment.trim(),
      })
      toast.success('该页已人工审核批准')
      setReviewPage(null)
      setReviewComment('')
      await load()
    } catch (e: any) {
      toast.error(e?.message || '审核失败')
    } finally {
      setReviewing(false)
    }
  }

  const onDownload = async (asset: LanhuEvidenceAsset) => {
    setDownloadingAssetId(asset.id)
    try {
      const blob = await downloadLanhuEvidenceAsset(asset.id)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = assetDownloadName(asset)
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      toast.error(e?.message || '下载失败')
    } finally {
      setDownloadingAssetId(null)
    }
  }

  const onRetry = async () => {
    if (!displayJobId) return
    try {
      const nextJob = await retryLanhuEvidenceJob(displayJobId)
      setDisplayJobId(nextJob.id)
      toast.success(`已创建重试任务 #${nextJob.id}`)
      await loadJob(nextJob.id)
    } catch (e: any) {
      toast.error(e?.message || '重试失败')
    }
  }

  const onImport = async () => {
    if (!job || !hasRequestedImport) return
    setImporting(true)
    try {
      await importLanhuEvidence(job.id, requestedImport)
      if (!quality.import_ready) {
        toast.success('已导入（部分页面存在质量问题，请检查导入结果）')
      } else {
        toast.success('已按请求选项完成导入')
      }
      await loadJob(job.id)
    } catch (e: any) {
      toast.error(e?.message || '导入失败')
    } finally {
      setImporting(false)
    }
  }

  const onCancel = async () => {
    if (!displayJobId) return
    try {
      await cancelLanhuEvidenceJob(displayJobId)
      toast.success('已请求取消')
      load()
    } catch (e: any) {
      toast.error(e?.message || '取消失败')
    }
  }

  const onDelete = async () => {
    if (!displayJobId) return
    try {
      await deleteLanhuEvidenceJob(displayJobId)
      toast.success('已删除任务')
      onOpenChange(false)
    } catch (e: any) {
      toast.error(e?.message || '删除失败')
    }
  }

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="w-[520px] sm:max-w-[520px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              证据包任务 {job ? `#${job.id}` : ''}
              {job && (
                <Badge variant="outline" className={STATUS_VARIANT[job.status] || ''}>
                  {job.status}
                </Badge>
              )}
              <Button size="sm" variant="ghost" onClick={load} disabled={loading} aria-label="刷新任务">
                {loading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
              </Button>
            </SheetTitle>
            <SheetDescription>{job?.source_url}</SheetDescription>
          </SheetHeader>

          {job && (
            <div className="space-y-4 py-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div>阶段：{job.stage}</div>
                <div>页面：{job.captured_pages}/{job.total_pages} 已采集</div>
                <div>OCR：{job.ocr_pages}/{job.total_pages}</div>
                <div>失败页：{job.failed_pages}</div>
                <div>完整性：{quality.complete ? '完整' : '需复核'}</div>
                <div>
                  导入状态：
                  <Badge
                    variant="outline"
                    className={quality.import_ready
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border-red-200 bg-red-50 text-red-700'}
                  >
                    {quality.import_ready ? '可导入' : '不可导入'}
                  </Badge>
                </div>
              </div>
              {job.error_message && <div className="text-xs text-red-600 break-all">错误：{job.error_message}</div>}
              <div className="space-y-1 text-xs" aria-label="质量阻断原因">
                {!!quality.pages_missing_capture?.length && (
                  <div className="text-red-600">缺少截图：{formatPageNumbers(quality.pages_missing_capture)}</div>
                )}
                {!!quality.pages_truncated?.length && (
                  <div className="text-red-600">滚动截断：{formatPageNumbers(quality.pages_truncated)}</div>
                )}
                {!!quality.pages_missing_text?.length && (
                  <div className="text-red-600">缺少有效文本：{formatPageNumbers(quality.pages_missing_text)}</div>
                )}
                {!!quality.pages_missing_ocr_review?.length && (
                  <div className="text-amber-700">
                    缺少 OCR 或人工审核：{formatPageNumbers(quality.pages_missing_ocr_review)}
                  </div>
                )}
              </div>

              {!!Object.keys(importResult).length && (
                <div
                  className={`rounded border px-2 py-1 text-xs ${importResult.error ? 'border-red-200 text-red-700' : 'border-emerald-200 text-emerald-700'}`}
                  aria-label="导入结果"
                >
                  {importResult.error
                    ? `导入失败：${String(importResult.error)}`
                    : `已导入：${Object.keys(importResult).join('、')}`}
                </div>
              )}

              {!!exportAssets.length && (
                <div className="border-t pt-2">
                  <div className="mb-1 font-medium">导出资产</div>
                  <div className="flex flex-wrap gap-2">
                    {exportAssets.map((asset) => (
                      <Button
                        key={asset.id}
                        size="sm"
                        variant="outline"
                        disabled={downloadingAssetId === asset.id}
                        onClick={() => onDownload(asset)}
                      >
                        {downloadingAssetId === asset.id && <Loader2 className="size-4 animate-spin" />}
                        下载 {asset.asset_type === 'word' ? 'Word' : 'JSON'}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              <div className="border-t pt-2">
                <div className="font-medium mb-1">页面列表（{pages.length}）</div>
                <div className="space-y-1 max-h-[40vh] overflow-y-auto">
                  {pages.map((p) => (
                    <div key={p.id} className="flex items-center justify-between gap-2 rounded border px-2 py-1">
                      <div className="min-w-0">
                        <div className="truncate" title={p.page_path}>{p.page_name || p.page_id}</div>
                        <div className="text-xs text-muted-foreground">
                          {p.segment_count} 段 · {p.capture_status}/{p.ocr_status}
                          {p.capture_truncated ? ' · 已截断' : ''}
                          {p.review_status === 'approved' ? ' · 已人工批准' : ''}
                        </div>
                      </div>
                      {hasPerm('lanhu_evidence:review')
                        && p.capture_status === 'success'
                        && p.merged_text.trim().length > 0
                        && p.ocr_status !== 'success'
                        && p.review_status !== 'approved' && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="shrink-0"
                            onClick={() => {
                              setReviewPage(p)
                              setReviewComment('')
                            }}
                          >
                            人工审核
                          </Button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          <SheetFooter className="gap-2">
            <Button variant="outline" onClick={onCancel}>取消任务</Button>
            <Button variant="outline" className="text-destructive hover:bg-destructive/10" onClick={onDelete}>删除任务</Button>
            {hasRequestedImport && !importCompleted
              && hasPerm('lanhu_evidence:import') && (
              <div className="space-y-2">
                {!quality.import_ready && (
                  <div className="rounded border border-amber-200 bg-amber-50 px-2 py-1.5 text-xs text-amber-700">
                    ⚠️ 证据包存在质量问题（缺截图/截断/缺文本/未审 OCR 页），导入结果可能不完整
                  </div>
                )}
                <Button variant="outline" disabled={importing} onClick={onImport}>
                  {importing && <Loader2 className="size-4 animate-spin" />}
                  执行导入
                </Button>
              </div>
            )}
            <Button onClick={onRetry}>重试</Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      <Dialog
        open={reviewPage !== null}
        onOpenChange={(nextOpen) => {
          if (!nextOpen && !reviewing) {
            setReviewPage(null)
            setReviewComment('')
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>批准 OCR 缺失页</DialogTitle>
            <DialogDescription>
              请确认已对照原始设计稿核验"{reviewPage?.page_name || reviewPage?.page_id}"，备注将保留在审计记录中。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label htmlFor="lanhu-review-comment" className="text-sm font-medium">审核备注</label>
            <Textarea
              id="lanhu-review-comment"
              value={reviewComment}
              maxLength={1000}
              placeholder="至少 3 个字符，说明核验依据"
              onChange={(event) => setReviewComment(event.target.value)}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              disabled={reviewing}
              onClick={() => {
                setReviewPage(null)
                setReviewComment('')
              }}
            >
              取消
            </Button>
            <Button disabled={reviewing || reviewComment.trim().length < 3} onClick={onReview}>
              {reviewing && <Loader2 className="size-4 animate-spin" />}
              批准该页
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
