import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
  Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  cancelLanhuEvidenceJob,
  fetchLanhuEvidenceJob,
  fetchLanhuEvidencePages,
  retryLanhuEvidenceJob,
} from '@/api/lanhuEvidence'
import type { LanhuEvidenceJob, LanhuEvidencePage } from '@/api/lanhuEvidence'
import { Loader2, RefreshCw } from '@/lib/icons'

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

function parseQuality(job: LanhuEvidenceJob | null): { complete?: boolean; pages_needing_review?: string[] } {
  if (!job?.quality_json) return {}
  try {
    return JSON.parse(job.quality_json)
  } catch {
    return {}
  }
}

/** 证据包任务详情抽屉 —— 状态 / 计数 / 质量 / 页面列表 / 重试·取消。 */
export default function LanhuEvidenceJobDrawer({ open, onOpenChange, jobId }: Props) {
  const [job, setJob] = useState<LanhuEvidenceJob | null>(null)
  const [pages, setPages] = useState<LanhuEvidencePage[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!jobId) return
    setLoading(true)
    try {
      const [j, p] = await Promise.all([
        fetchLanhuEvidenceJob(jobId),
        fetchLanhuEvidencePages(jobId),
      ])
      setJob(j)
      setPages(p.items)
    } catch (e: any) {
      toast.error(e?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [jobId])

  useEffect(() => {
    if (open && jobId) load()
  }, [open, jobId, load])

  const quality = parseQuality(job)

  const onRetry = async () => {
    if (!jobId) return
    try {
      await retryLanhuEvidenceJob(jobId)
      toast.success('已重新排队')
      load()
    } catch (e: any) {
      toast.error(e?.message || '重试失败')
    }
  }

  const onCancel = async () => {
    if (!jobId) return
    try {
      await cancelLanhuEvidenceJob(jobId)
      toast.success('已请求取消')
      load()
    } catch (e: any) {
      toast.error(e?.message || '取消失败')
    }
  }

  return (
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
            <Button size="sm" variant="ghost" onClick={load} disabled={loading}>
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
            </div>
            {job.word_path && <div className="text-xs text-muted-foreground break-all">Word：{job.word_path}</div>}
            {job.json_path && <div className="text-xs text-muted-foreground break-all">JSON：{job.json_path}</div>}
            {job.error_message && <div className="text-xs text-red-600 break-all">错误：{job.error_message}</div>}
            {!!quality.pages_needing_review?.length && (
              <div className="text-xs text-amber-600">
                待复核页面：{quality.pages_needing_review.join('、')}
              </div>
            )}

            <div className="border-t pt-2">
              <div className="font-medium mb-1">页面列表（{pages.length}）</div>
              <div className="space-y-1 max-h-[40vh] overflow-y-auto">
                {pages.map((p) => (
                  <div key={p.id} className="flex items-center justify-between rounded border px-2 py-1">
                    <span className="truncate mr-2" title={p.page_path}>{p.page_name || p.page_id}</span>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {p.segment_count} 段 · {p.capture_status}/{p.ocr_status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <SheetFooter className="gap-2">
          <Button variant="outline" onClick={onCancel}>取消任务</Button>
          <Button onClick={onRetry}>重试</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
