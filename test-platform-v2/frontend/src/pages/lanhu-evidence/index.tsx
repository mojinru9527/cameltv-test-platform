import { useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth'
import {
  createLanhuEvidenceJob,
  fetchLanhuEvidenceJobs,
  cancelLanhuEvidenceJob,
  retryLanhuEvidenceJob,
  deleteLanhuEvidenceJob,
  type LanhuEvidenceJob,
} from '@/api/lanhuEvidence'
import { Button, Input, Badge, Label } from '@/ui'
import { Switch } from '@/components/ui/switch'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
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
import { Plus, Eye, RotateCcw, XCircle, Trash2, Loader2 } from '@/lib/icons'
import { jobStatusLabel, jobStatusTone, stageLabel } from './labels'

const IMPORT_OPTIONS: { key: 'import_to_requirement' | 'import_to_knowledge' | 'import_to_wiki'; label: string }[] = [
  { key: 'import_to_requirement', label: '导入需求文档' },
  { key: 'import_to_knowledge', label: '导入知识库（RAG）' },
  { key: 'import_to_wiki', label: '导入 Wiki' },
]

function emptyForm() {
  return {
    url: '',
    capture_all_pages: true,
    include_word: true,
    include_json: true,
    import_to_requirement: false,
    import_to_knowledge: false,
    import_to_wiki: false,
  }
}

export default function LanhuEvidencePage() {
  useDocumentTitle('蓝湖证据包')
  const navigate = useNavigate()
  const canRun = useAuthStore((state) => state.hasPerm)('lanhu_evidence:run')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [form, setForm] = useState(emptyForm())
  const [saving, setSaving] = useState(false)
  const { data, isLoading, isError, error, refetch } = useApi(
    () => fetchLanhuEvidenceJobs(),
    [],
  )
  const jobs = data?.items || []

  const openCreate = () => {
    setForm(emptyForm())
    setDialogOpen(true)
  }

  const handleCreate = async () => {
    const url = form.url.trim()
    if (!url) {
      toast.error('请输入蓝湖链接')
      return
    }
    if (!/^https?:\/\//.test(url)) {
      toast.error('请输入以 http(s):// 开头的蓝湖链接')
      return
    }
    setSaving(true)
    try {
      await createLanhuEvidenceJob({ ...form, url })
      toast.success('证据包任务已创建，后台开始采集')
      setDialogOpen(false)
      refetch()
    } catch {
      // error toast handled by client interceptor
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = async (job: LanhuEvidenceJob) => {
    try {
      await cancelLanhuEvidenceJob(job.id)
      toast.success('已请求取消')
      refetch()
    } catch {
      // handled by interceptor
    }
  }

  const handleRetry = async (job: LanhuEvidenceJob) => {
    try {
      await retryLanhuEvidenceJob(job.id)
      toast.success('已创建重试任务')
      refetch()
    } catch {
      // handled by interceptor
    }
  }

  const handleDelete = async (job: LanhuEvidenceJob) => {
    try {
      await deleteLanhuEvidenceJob(job.id)
      toast.success('任务已删除')
      refetch()
    } catch {
      // handled by interceptor
    }
  }

  const canInterrupt = (job: LanhuEvidenceJob) =>
    canRun && (job.status === 'pending' || job.status === 'running')

  return (
    <div>
      <PageHeader
        title="蓝湖证据包"
        description="采集蓝湖设计稿（截图 + OCR）→ 人工审核 → 导入需求 / RAG / Wiki"
      >
        {canRun && (
          <Button size="sm" className="min-h-11" onClick={openCreate} data-icon="inline-start">
            <Plus />
            新建采集任务
          </Button>
        )}
      </PageHeader>

      <div className="mt-6">
        <AsyncState
          isLoading={isLoading}
          isError={isError}
          error={error}
          data={jobs.length > 0 ? jobs : undefined}
          onRetry={refetch}
          emptyTitle="暂无证据包任务"
          emptyDescription="点击「新建采集任务」，粘贴蓝湖项目/设计稿链接即可开始"
          emptyAction={canRun ? { label: '新建采集任务', onClick: openCreate } : undefined}
          loadingVariant="skeleton"
          skeletonType="table"
          loadingRows={4}
        >
          {(items) => (
            <div className="rounded-xl border bg-card">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">ID</TableHead>
                    <TableHead>文档 / 来源</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>阶段</TableHead>
                    <TableHead>页面（捕获/OCR）</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead className="w-[180px]">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((job) => (
                    <TableRow key={job.id}>
                      <TableCell className="text-xs text-muted-foreground">#{job.id}</TableCell>
                      <TableCell className="max-w-[260px]">
                        <div className="truncate font-medium" title={job.document_name || job.source_url}>
                          {job.document_name || '（未命名）'}
                        </div>
                        <div className="truncate text-xs text-muted-foreground">{job.source_url}</div>
                      </TableCell>
                      <TableCell>
                        <Badge tone={jobStatusTone(job.status)}>{jobStatusLabel(job.status)}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {stageLabel(job.stage)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {job.captured_pages}/{job.total_pages} 页 · OCR {job.ocr_pages}
                        {job.failed_pages > 0 && (
                          <span className="ml-1 text-status-danger">失败 {job.failed_pages}</span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {job.created_at ? new Date(job.created_at).toLocaleString() : '—'}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            aria-label={`查看任务 ${job.id} 详情`}
                            onClick={() => navigate(`/lanhu-evidence/${job.id}`)}
                          >
                            <Eye className="size-4" />
                          </Button>
                          {canInterrupt(job) && (
                            <Button
                              size="sm"
                              variant="ghost"
                              aria-label={`取消任务 ${job.id}`}
                              onClick={() => handleCancel(job)}
                            >
                              <XCircle className="size-4" />
                            </Button>
                          )}
                          {canRun && job.status === 'failed' && (
                            <Button
                              size="sm"
                              variant="ghost"
                              aria-label={`重试任务 ${job.id}`}
                              onClick={() => handleRetry(job)}
                            >
                              <RotateCcw className="size-4" />
                            </Button>
                          )}
                          {canRun && (
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button size="sm" variant="ghost" aria-label={`删除任务 ${job.id}`}>
                                  <Trash2 className="size-4 text-destructive" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>确定删除？</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    将删除证据包任务 #{job.id} 及其页面/截图/OCR 数据，此操作不可撤销。
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>取消</AlertDialogCancel>
                                  <AlertDialogAction variant="destructive" onClick={() => handleDelete(job)}>
                                    删除
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
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

      {/* ── 新建任务 Dialog ── */}
      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setDialogOpen(false) }}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader>
            <DialogTitle>新建采集任务</DialogTitle>
            <DialogDescription>
              支持蓝湖项目级链接（自动识别设计图板）或具体设计稿链接
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4 py-2">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="le-url">蓝湖链接</Label>
              <Input
                id="le-url"
                placeholder="https://lanhuapp.com/web/#/item/project/stage?tid=…&pid=…"
                value={form.url}
                onChange={(e) => setForm((prev) => ({ ...prev, url: e.target.value }))}
              />
            </div>

            <div className="flex flex-col gap-2 rounded-lg border p-3">
              <span className="text-sm font-medium">采集选项</span>
              <label className="flex items-center justify-between text-sm">
                <span>捕获全部页面</span>
                <Switch
                  checked={form.capture_all_pages}
                  onCheckedChange={(v) => setForm((prev) => ({ ...prev, capture_all_pages: v }))}
                />
              </label>
              <label className="flex items-center justify-between text-sm">
                <span>导出 Word 文档</span>
                <Switch
                  checked={form.include_word}
                  onCheckedChange={(v) => setForm((prev) => ({ ...prev, include_word: v }))}
                />
              </label>
              <label className="flex items-center justify-between text-sm">
                <span>导出 JSON 证据</span>
                <Switch
                  checked={form.include_json}
                  onCheckedChange={(v) => setForm((prev) => ({ ...prev, include_json: v }))}
                />
              </label>
            </div>

            <div className="flex flex-col gap-2 rounded-lg border p-3">
              <span className="text-sm font-medium">质量门禁通过后自动导入（需 lanhu_evidence:import 权限）</span>
              {IMPORT_OPTIONS.map((opt) => (
                <label key={opt.key} className="flex items-center gap-2 text-sm cursor-pointer">
                  <Checkbox
                    checked={form[opt.key]}
                    onCheckedChange={(v) =>
                      setForm((prev) => ({ ...prev, [opt.key]: Boolean(v) }))
                    }
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button disabled={saving} onClick={handleCreate} data-icon="inline-start">
              {saving && <Loader2 className="animate-spin" />}
              创建任务
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
