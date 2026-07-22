import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
  Card, CardContent, CardFooter, CardHeader, CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  cancelLanhuEvidenceJob,
  deleteLanhuEvidenceJob,
  fetchLanhuEvidenceJobs,
  retryLanhuEvidenceJob,
} from '@/api/lanhuEvidence'
import type { LanhuEvidenceJob } from '@/api/lanhuEvidence'
import {
  Loader2, Plus, RefreshCw, XCircle, CheckCircle2, AlertTriangle, Clock, ExternalLink, Trash2, Image,
} from '@/lib/icons'
import { cn } from '@/lib/utils'

interface Props {
  /** Fired when user clicks "查看功能拆分" on a successful job */
  onViewExtraction?: (job: LanhuEvidenceJob) => void
  /** Fired when user clicks "查看截图" on a successful job (batch-28) */
  onViewScreenshots?: (job: LanhuEvidenceJob) => void
  /** Trigger open the create dialog */
  onNewTask?: () => void
}

const STATUS_VARIANT: Record<string, { variant: 'secondary' | 'destructive' | 'outline' | 'default'; className?: string; label: string }> = {
  pending:   { variant: 'secondary', label: '等待中' },
  running:   { variant: 'default', className: 'bg-blue-100 text-blue-700 border-blue-200', label: '采集中' },
  success:   { variant: 'default', className: 'bg-emerald-100 text-emerald-700 border-emerald-200', label: '已完成' },
  success_with_warnings: { variant: 'default', className: 'bg-amber-100 text-amber-700 border-amber-200', label: '部分完成' },
  failed:    { variant: 'destructive', label: '失败' },
  cancelled: { variant: 'outline', label: '已取消' },
}

const STAGE_LABELS: Record<string, string> = {
  queued: '排队中',
  discovering: '发现页面',
  capturing: '截图中',
  ocr: 'OCR 识别',
  merging: '合并文本',
  exporting: '导出文件',
  evaluating: '质量检查',
  importing: '导入中',
  done: '完成',
}

/** 阶段顺序（用于进度百分比） */
const STAGE_ORDER = [
  'queued', 'discovering', 'capturing', 'ocr', 'merging',
  'exporting', 'evaluating', 'importing', 'done',
]

const POLL_INTERVAL_MS = 3000

function stageProgress(stage: string): number {
  const idx = STAGE_ORDER.indexOf(stage)
  if (idx < 0) return 0
  return Math.round(((idx + 1) / STAGE_ORDER.length) * 100)
}

function relativeTime(dateStr?: string | null): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return '刚刚'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} 分钟前`
  const hrs = Math.floor(min / 60)
  if (hrs < 24) return `${hrs} 小时前`
  return `${Math.floor(hrs / 24)} 天前`
}

function parseVersion(sourceUrl: string): string {
  const m = sourceUrl.match(/\/updates\/([\d.]+)/) || sourceUrl.match(/[?&]v(?:ersion)?=([\d.]+)/)
  return m ? `v${m[1]}` : ''
}

export default function EvidenceTaskPanel({ onViewExtraction, onNewTask }: Props) {
  const [jobs, setJobs] = useState<LanhuEvidenceJob[]>([])
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  const loadJobs = useCallback(async () => {
    try {
      const data = await fetchLanhuEvidenceJobs({ page: 1, page_size: 50 })
      setJobs(data.items || [])
    } catch {
      // silent — interceptor handles auth errors
    }
  }, [])

  // Initial load + polling
  useEffect(() => {
    setLoading(true)
    loadJobs().finally(() => setLoading(false))

    const timer = setInterval(loadJobs, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [loadJobs])

  // Active job (running or pending)
  const activeJob = jobs.find((j) => j.status === 'running' || j.status === 'pending')

  const handleCancel = async (jobId: number) => {
    setActionLoading(jobId)
    try {
      await cancelLanhuEvidenceJob(jobId)
      toast.success('已取消任务')
      loadJobs()
    } catch (e: any) {
      toast.error(e?.message || '取消失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleRetry = async (jobId: number) => {
    setActionLoading(jobId)
    try {
      await retryLanhuEvidenceJob(jobId)
      toast.success('已重新提交任务')
      loadJobs()
    } catch (e: any) {
      toast.error(e?.message || '重试失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async (jobId: number) => {
    setActionLoading(jobId)
    try {
      await deleteLanhuEvidenceJob(jobId)
      toast.success('已删除任务')
      loadJobs()
    } catch (e: any) {
      toast.error(e?.message || '删除失败')
    } finally {
      setActionLoading(null)
    }
  }

  // ── Sort: active first, then newest first ──
  const sorted = [...jobs].sort((a, b) => {
    const aActive = a.status === 'running' || a.status === 'pending' ? 0 : 1
    const bActive = b.status === 'running' || b.status === 'pending' ? 0 : 1
    if (aActive !== bActive) return aActive - bActive
    return (b.id || 0) - (a.id || 0)
  })

  return (
    <Card size="sm" className="w-[260px] shrink-0 h-[calc(100vh-215px)] flex flex-col">
      <CardHeader className="border-b pb-2 shrink-0">
        <CardTitle className="text-[13px] flex items-center justify-between">
          证据任务
          {activeJob && (
            <span className="relative flex size-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-blue-500" />
            </span>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 min-h-0 overflow-y-auto p-0">
        {loading && jobs.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-muted-foreground text-sm">
            <Loader2 className="size-4 animate-spin mr-2" />
            加载中...
          </div>
        ) : sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground text-sm gap-2">
            <Clock className="size-5" />
            <span>暂无采集任务</span>
            <span className="text-xs">点击下方按钮创建</span>
          </div>
        ) : (
          <div className="divide-y">
            {sorted.map((job) => {
              const statusInfo = STATUS_VARIANT[job.status] || STATUS_VARIANT.pending
              const isActive = job.status === 'running' || job.status === 'pending'
              const isDone = job.status === 'success' || job.status === 'success_with_warnings'
              const isFailed = job.status === 'failed'
              const version = parseVersion(job.source_url)

              return (
                <div
                  key={job.id}
                  className={cn(
                    'px-3 py-2.5 space-y-1.5 transition-colors',
                    isActive && 'bg-blue-50/50',
                    isFailed && 'bg-red-50/30',
                  )}
                >
                  {/* Top row: version + status */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium truncate">
                      {version || `#${job.id}`}
                    </span>
                    <Badge
                      variant={statusInfo.variant}
                      className={cn(
                        'text-[10px] px-1.5 py-0 h-5',
                        statusInfo.className,
                        isActive && 'animate-pulse',
                      )}
                    >
                      {statusInfo.label}
                    </Badge>
                  </div>

                  {/* Stage + progress for active jobs */}
                  {isActive && (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                        <span>{STAGE_LABELS[job.stage] || job.stage}</span>
                        <span>
                          {job.captured_pages > 0 && `${job.captured_pages}/${job.total_pages} 页`}
                        </span>
                      </div>
                      <Progress value={stageProgress(job.stage)} className="h-1.5" />
                    </div>
                  )}

                  {/* Error message for failed */}
                  {isFailed && job.error_message && (
                    <p className="text-[10px] text-destructive line-clamp-2 leading-tight">
                      {job.error_message === 'worker_lost' ? 'Worker 丢失，任务超时未响应' : job.error_message}
                    </p>
                  )}

                  {/* Timestamp */}
                  <p className="text-[10px] text-muted-foreground">
                    {relativeTime(job.created_at)}
                    {job.attempt_no > 1 && ` · 第 ${job.attempt_no} 次`}
                  </p>

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 pt-0.5">
                    {isFailed && (
                      <Button
                        size="xs"
                        variant="outline"
                        className="h-6 text-[10px] px-2"
                        disabled={actionLoading === job.id}
                        onClick={() => handleRetry(job.id)}
                      >
                        {actionLoading === job.id ? (
                          <Loader2 className="size-3 animate-spin mr-0.5" />
                        ) : (
                          <RefreshCw className="size-3 mr-0.5" />
                        )}
                        重试
                      </Button>
                    )}
                    {isActive && (
                      <Button
                        size="xs"
                        variant="ghost"
                        className="h-6 text-[10px] px-2 text-destructive hover:bg-destructive/10"
                        disabled={actionLoading === job.id}
                        onClick={() => handleCancel(job.id)}
                      >
                        <XCircle className="size-3 mr-0.5" />
                        取消
                      </Button>
                    )}
                    {isDone && onViewExtraction && (() => {
                      let hasDocId = false
                      try {
                        const ir = job.import_result_json ? JSON.parse(job.import_result_json) : null
                        hasDocId = !!ir?.requirement_doc_id
                      } catch { /* parse error, hide button */ }
                      return hasDocId ? (
                        <Button
                          size="xs"
                          variant="outline"
                          className="h-6 text-[10px] px-2"
                          onClick={() => onViewExtraction(job)}
                        >
                          <ExternalLink className="size-3 mr-0.5" />
                          查看功能拆分
                        </Button>
                      ) : null
                    })()}
                    {isDone && onViewScreenshots && (
                      <Button
                        size="xs"
                        variant="outline"
                        className="h-6 text-[10px] px-2"
                        onClick={() => onViewScreenshots(job)}
                      >
                        <Image className="size-3 mr-0.5" />
                        查看截图
                      </Button>
                    )}
                    {!isActive && (
                      <Button
                        size="xs"
                        variant="ghost"
                        className="h-6 text-[10px] px-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 ml-auto"
                        disabled={actionLoading === job.id}
                        onClick={() => handleDelete(job.id)}
                      >
                        <Trash2 className="size-3" />
                      </Button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>

      <CardFooter className="border-t pt-2 pb-2 shrink-0">
        <Button
          size="sm"
          variant="outline"
          className="w-full text-xs h-7"
          onClick={onNewTask}
        >
          <Plus className="size-3.5 mr-1" />
          新建采集
        </Button>
      </CardFooter>
    </Card>
  )
}
