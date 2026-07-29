import {
  Edit,
  Eye,
  Monitor,
  Play,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  Loader2,
  XCircle,
  FileText,
  Image,
  Video,
  Download,
  Terminal,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Ban,
} from '@/lib/icons'
import { useCallback, useEffect, useRef, useState } from 'react'
import { createUiJob, deleteUiJob, fetchUiJob, fetchUiJobs, fetchUiRuns, triggerUiJob, updateUiJob, fetchScripts, fetchRunDetail, cancelRun, fetchRunArtifacts } from '@/api/uitest'
import { fetchEnvironments } from '@/api/environment'
import { useAuthStore } from '@/stores/auth'
import useAbortableEffect, { rethrowUnlessAborted } from '@/hooks/useAbortableEffect'
import type { Environment, UiJobItem, UiRunItem, UiRunArtifact } from '@/types'
import { toast } from 'sonner'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import DataTable, { type DataTableColumn } from '@/components/DataTable'
import PageHeader from '@/components/PageHeader'
import { Button } from '@/ui'
import { Input } from '@/ui'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Dialog,
  DialogContent,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const BROWSER_MAP: Record<string, { color: string }> = {
  chromium: { color: 'blue' },
  firefox: { color: 'orange' },
  webkit: { color: 'purple' },
}

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  idle: { color: 'default', label: '待执行' },
  running: { color: 'processing', label: '运行中' },
  done: { color: 'green', label: '已完成' },
  fail: { color: 'red', label: '失败' },
}

const RUN_STATUS_MAP: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '等待中' },
  running: { color: 'processing', label: '运行中' },
  done: { color: 'green', label: '完成' },
  fail: { color: 'red', label: '失败' },
  cancelled: { color: 'yellow', label: '已取消' },
}

function browserBadgeClass(c: string) {
  const map: Record<string, string> = {
    blue: 'border-status-info-border bg-status-info-muted text-status-info dark:border-status-info-border dark:bg-status-info-muted dark:text-status-info',
    orange: 'border-status-warning-border bg-status-warning-muted text-status-warning dark:border-status-warning-border dark:bg-status-warning-muted dark:text-status-warning',
    purple: 'border-status-accent-border bg-status-accent-muted text-status-accent dark:border-status-accent-border dark:bg-status-accent-muted dark:text-status-accent',
  }
  return map[c] ?? ''
}

function statusBadgeClass(c: string) {
  const map: Record<string, string> = {
    default: 'border-border bg-muted text-muted-foreground',
    processing: 'border-status-info-border bg-status-info-muted text-status-info dark:border-status-info-border dark:bg-status-info-muted dark:text-status-info',
    green: 'border-status-success-border bg-status-success-muted text-status-success dark:border-status-success-border dark:bg-status-success-muted dark:text-status-success',
    red: 'border-status-danger-border bg-status-danger-muted text-status-danger dark:border-status-danger-border dark:bg-status-danger-muted dark:text-status-danger',
    yellow: 'border-status-warning-border bg-status-warning-muted text-status-warning dark:border-status-warning-border dark:bg-status-warning-muted dark:text-status-warning',
  }
  return map[c] ?? ''
}

const uiJobFormSchema = z.object({
  name: z.string().min(1, '请输入任务名称'),
  description: z.string().optional().default(''),
  test_spec: z.string().optional().default(''),
  browser: z.string().default('chromium'),
  environment_id: z.number().nullable().default(null),
})

type UiJobFormValues = z.infer<typeof uiJobFormSchema>

export default function UiTestPage() {
  useDocumentTitle('UI 测试')
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [data, setData] = useState({ total: 0, items: [] as UiJobItem[], page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [fStatus, setFStatus] = useState<string | undefined>()
  const [fKeyword, setFKeyword] = useState('')
  const [scripts, setScripts] = useState<string[]>([])
  const [environments, setEnvironments] = useState<Environment[]>([])

  useAbortableEffect((signal) => {
    fetchScripts(signal)
      .then((rows) => { if (!signal.aborted) setScripts(rows) })
      .catch(() => { if (!signal.aborted) setScripts([]) })
  }, [])
  useAbortableEffect((signal) => {
    fetchEnvironments(signal)
      .then((rows) => { if (!signal.aborted) setEnvironments(rows) })
      .catch(() => { if (!signal.aborted) setEnvironments([]) })
  }, [])

  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<UiJobItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  const [detail, setDetail] = useState<any>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [runs, setRuns] = useState({ total: 0, items: [] as UiRunItem[] })

  // Run detail state
  const [selectedRun, setSelectedRun] = useState<UiRunItem | null>(null)
  const [runDetailOpen, setRunDetailOpen] = useState(false)
  const [runArtifacts, setRunArtifacts] = useState<UiRunArtifact[]>([])
  const [runDetailLoading, setRunDetailLoading] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Auto-poll run detail while running/pending
  useEffect(() => {
    if (!selectedRun || !runDetailOpen) return
    if (selectedRun.status !== 'pending' && selectedRun.status !== 'running') return

    pollRef.current = setInterval(async () => {
      try {
        const fresh = await fetchRunDetail(selectedRun.id)
        setSelectedRun(fresh)
        if (fresh.status !== 'pending' && fresh.status !== 'running') {
          // Load artifacts when done
          try {
            const arts = await fetchRunArtifacts(selectedRun.id)
            setRunArtifacts(arts)
          } catch { /* ignore */ }
        }
      } catch { /* ignore */ }
    }, 3000)

    return () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    }
  }, [selectedRun?.id, selectedRun?.status, runDetailOpen])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const form = useForm<UiJobFormValues>({
    resolver: zodResolver(uiJobFormSchema),
    defaultValues: { name: '', description: '', test_spec: '', browser: 'chromium', environment_id: null },
  })

  // ── DataTable column definitions ──
  const uiJobColumns: DataTableColumn<UiJobItem>[] = [
    { key: 'name', header: '名称', className: 'max-w-0', render: (r) => (
      <button
        className="text-primary hover:underline text-left truncate cursor-pointer bg-transparent border-0 p-0"
        onClick={() => openDetail(r)}
      >
        {r.name}
      </button>
    )},
    { key: 'test_spec', header: '测试文件', headerClassName: 'w-[200px]', className: 'max-w-[200px] truncate', render: (r) => r.test_spec || '-' },
    { key: 'browser', header: '浏览器', headerClassName: 'w-[100px]', render: (r) => (
      <Badge tone="neutral" className={browserBadgeClass(BROWSER_MAP[r.browser]?.color)}>
        <Monitor className="size-3" />
        {r.browser}
      </Badge>
    )},
    { key: 'status', header: '状态', headerClassName: 'w-[100px]', render: (r) => (
      <Badge tone="neutral" className={statusBadgeClass(STATUS_MAP[r.status]?.color)}>
        {STATUS_MAP[r.status]?.label || r.status}
      </Badge>
    )},
    { key: 'last_run_time', header: '上次执行', headerClassName: 'w-[170px]', render: (r) => r.last_run_time ? new Date(r.last_run_time).toLocaleString('zh-CN') : '-' },
    { key: 'actions', header: '操作', headerClassName: 'w-[240px]', render: (r) => (
      <div className="flex items-center gap-1">
        <Button size="xs" variant="secondary" onClick={() => openDetail(r)}>
          <Eye className="size-3" />
          详情
        </Button>
        {hasPerm('uitest:update') && (
          <Button size="xs" variant="secondary" onClick={() => openEdit(r)}>
            <Edit className="size-3" />
            编辑
          </Button>
        )}
        {hasPerm('uitest:trigger') && (
          <Button size="xs" variant="secondary" onClick={() => doTrigger(r.id)} disabled={r.status === 'running'}>
            <Play className="size-3" />
            执行
          </Button>
        )}
        {hasPerm('uitest:delete') && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button size="xs" variant="secondary" className="text-destructive border-destructive/20 hover:bg-destructive/10" onClick={() => setDeleteTarget(r.id)}>
                <Trash2 className="size-3" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>确定删除？</AlertDialogTitle>
                <AlertDialogDescription>此操作不可撤销。</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel onClick={() => setDeleteTarget(null)}>取消</AlertDialogCancel>
                <AlertDialogAction onClick={doDelete}>确定删除</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
      </div>
    )},
  ]

  const load = useCallback(async (page = 1, signal?: AbortSignal) => {
    setLoading(true)
    try {
      const params: any = { page, page_size: 20 }
      if (fStatus) params.status = fStatus
      if (fKeyword) params.keyword = fKeyword
      const r: any = await fetchUiJobs(params, signal)
      if (!signal?.aborted) setData(r)
    } catch (error) {
      rethrowUnlessAborted(error, signal)
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [fStatus, fKeyword])

  useAbortableEffect((signal) => { void load(1, signal) }, [load])

  const doSave = async (vals: UiJobFormValues) => {
    setSaving(true)
    try {
      if (editing?.id) {
        await updateUiJob(editing.id, vals)
        toast.success('已更新')
      } else {
        await createUiJob(vals)
        toast.success('已创建')
      }
      setDrawer(false)
      form.reset()
      load()
    } finally { setSaving(false) }
  }

  const doTrigger = async (id: number) => {
    await triggerUiJob(id)
    toast.success('执行已触发')
    load()
  }

  const doDelete = async () => {
    if (deleteTarget == null) return
    await deleteUiJob(deleteTarget)
    toast.success('已删除')
    setDeleteTarget(null)
    load()
  }

  const openDetail = async (r: UiJobItem) => {
    try {
      const jobDetail: any = await fetchUiJob(r.id)
      setDetail(jobDetail)
      const runsData: any = await fetchUiRuns(r.id)
      setRuns(runsData)
      setDetailOpen(true)
    } catch { /* ignore */ }
  }

  const openRunDetail = async (run: UiRunItem) => {
    setSelectedRun(run)
    setRunDetailOpen(true)
    setRunDetailLoading(true)
    try {
      const [fresh, arts] = await Promise.all([
        fetchRunDetail(run.id),
        fetchRunArtifacts(run.id).catch(() => []),
      ])
      setSelectedRun(fresh)
      setRunArtifacts(arts)
    } catch { /* ignore */ }
    finally { setRunDetailLoading(false) }
  }

  const handleCancelRun = async () => {
    if (!selectedRun) return
    try {
      await cancelRun(selectedRun.id)
      toast.success('已请求取消')
      const fresh = await fetchRunDetail(selectedRun.id)
      setSelectedRun(fresh)
    } catch { setRunDetailLoading(false) }
  }

  const openEdit = (r: UiJobItem) => {
    setEditing(r)
    form.reset({
      name: r.name ?? '',
      description: r.description ?? '',
      test_spec: r.test_spec ?? '',
      browser: r.browser ?? 'chromium',
      environment_id: r.environment_id ?? null,
    })
    setDrawer(true)
  }

  return (
    <div className="space-y-4">
      <PageHeader title="UI 测试" />

      <DataTable
        columns={uiJobColumns}
        data={data.items}
        rowKey={(r) => r.id}
        loading={loading}
        loadingRows={4}
        emptyState={{ title: '暂无 UI 测试任务', description: '点击「新建任务」创建 UI 自动化测试' }}
        pagination={{
          page: data.page,
          totalPages: Math.max(1, Math.ceil(data.total / data.page_size)),
          total: data.total,
          onChange: (p) => load(p),
        }}
        toolbar={
          <div className="flex items-center gap-2 flex-wrap">
            <Select value={fStatus ?? '__all__'} onValueChange={(v) => setFStatus(v === '__all__' ? undefined : v)}>
              <SelectTrigger className="w-[130px]">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部</SelectItem>
                {Object.entries(STATUS_MAP).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex items-center gap-1">
              <Input
                placeholder="搜索任务名"
                className="w-[240px]"
                value={fKeyword}
                onChange={(e) => setFKeyword(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') load() }}
              />
              <Button size="icon-sm" variant="ghost" onClick={() => load()} aria-label="搜索 UI 测试任务">
                <Search className="size-4" />
              </Button>
            </div>

            <Button variant="secondary" size="md" onClick={() => load()}>
              <RotateCcw className="size-4" />
              刷新
            </Button>
            {hasPerm('uitest:create') && (
              <Button onClick={() => { form.reset({ name: '', description: '', test_spec: '', browser: 'chromium', environment_id: null }); setEditing(null); setDrawer(true) }}>
                <Plus className="size-4" />
                新建任务
              </Button>
            )}
          </div>
        }
      />

      {/* Create/Edit Dialog */}
      <Dialog open={drawer} onOpenChange={(open) => { if (!open) { setDrawer(false); setEditing(null); form.reset() } }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing?.id ? '编辑UI测试任务' : '新建UI测试任务'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={form.handleSubmit(doSave)} className="flex flex-col gap-4">
            <div data-invalid={!!form.formState.errors.name} aria-invalid={!!form.formState.errors.name}>
              <label className="text-sm font-medium mb-1 block">任务名称</label>
              <Input placeholder="如：首页推荐冒烟测试" {...form.register('name')} />
              {form.formState.errors.name && (
                <p className="text-xs text-destructive mt-0.5">{form.formState.errors.name.message}</p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">描述</label>
              <Textarea rows={3} placeholder="测试说明" {...form.register('description')} />
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">测试脚本</label>
              <ScriptSelector
                value={form.watch('test_spec') || ''}
                onChange={(v) => form.setValue('test_spec', v)}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">浏览器</label>
              <Select value={form.watch('browser')} onValueChange={(v) => form.setValue('browser', v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.keys(BROWSER_MAP).map((k) => (
                    <SelectItem key={k} value={k}>{k}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">运行环境</label>
              <Select
                value={form.watch('environment_id') == null ? '__none__' : String(form.watch('environment_id'))}
                onValueChange={(v) => form.setValue('environment_id', v === '__none__' ? null : Number(v))}
              >
                <SelectTrigger aria-label="运行环境">
                  <SelectValue placeholder="选择运行环境" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">不绑定环境</SelectItem>
                  {environments.map((env) => (
                    <SelectItem key={env.id} value={String(env.id)}>
                      {env.name}（{env.base_url || '未配置 Base URL'}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground mt-1">
                执行时会把所选环境的 Base URL 注入 Playwright。
              </p>
            </div>

            <DialogFooter>
              <Button type="button" variant="secondary" onClick={() => { setDrawer(false); setEditing(null); form.reset() }}>
                取消
              </Button>
              <Button type="submit" disabled={saving}>
                {saving && <Loader2 className="size-4 animate-spin" />}
                保存
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Detail Sheet */}
      <Sheet open={detailOpen} onOpenChange={(open) => { if (!open) { setDetailOpen(false); setDetail(null) } }}>
        <SheetContent className="sm:max-w-3xl">
          <SheetHeader>
            <SheetTitle>任务详情</SheetTitle>
          </SheetHeader>
          {detail && (
            <div className="flex flex-col gap-4 mt-4 overflow-y-auto flex-1">
              <dl className="grid grid-cols-2 border rounded-lg">
                {[
                  ['名称', detail.name],
                  ['浏览器', <Badge key="br" tone="neutral" className={browserBadgeClass(BROWSER_MAP[detail.browser]?.color)}><Monitor className="size-3" />{detail.browser}</Badge>],
                  ['状态', <Badge key="st" tone="neutral" className={statusBadgeClass(STATUS_MAP[detail.status]?.color)}>{STATUS_MAP[detail.status]?.label}</Badge>],
                  ['测试文件', detail.test_spec || '-'],
                ].map(([label, value]) => (
                  <div key={label as string} className="flex flex-col border-b border-r p-2 even:border-r-0 [&:nth-last-child(-n+2)]:border-b-0">
                    <dt className="text-xs text-muted-foreground">{label}</dt>
                    <dd className="text-sm mt-0.5">{value}</dd>
                  </div>
                ))}
                <div className="flex flex-col border-b border-r p-2 even:border-r-0 col-span-2 border-r-0 border-b-0">
                  <dt className="text-xs text-muted-foreground">描述</dt>
                  <dd className="text-sm mt-0.5">{detail.description || '-'}</dd>
                </div>
              </dl>

              {hasPerm('uitest:trigger') && (
                <div>
                  <Button onClick={async () => { await doTrigger(detail.id); await openDetail(detail) }}>
                    <Play className="size-4" />
                    执行测试
                  </Button>
                </div>
              )}

              <Tabs defaultValue="runs">
                <TabsList>
                  <TabsTrigger value="runs">运行历史 ({runs.total})</TabsTrigger>
                  <TabsTrigger value="result">最新结果</TabsTrigger>
                </TabsList>
                <TabsContent value="runs" className="mt-3">
                  <div className="rounded-lg border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[80px]">状态</TableHead>
                          <TableHead className="w-[170px]">开始时间</TableHead>
                          <TableHead className="w-[170px]">结束时间</TableHead>
                          <TableHead className="w-[200px]">结果</TableHead>
                          <TableHead className="w-[120px]">Trace</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {runs.items.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={5} className="text-center py-4 text-muted-foreground">暂无数据</TableCell>
                          </TableRow>
                        ) : (
                          runs.items.map((run) => (
                            <TableRow key={run.id} className="cursor-pointer hover:bg-muted/50" onClick={() => openRunDetail(run)}>
                              <TableCell>
                                <Badge tone="neutral" className={statusBadgeClass(RUN_STATUS_MAP[run.status]?.color)}>
                                  {RUN_STATUS_MAP[run.status]?.label || run.status}
                                </Badge>
                              </TableCell>
                              <TableCell>{run.started_at ? new Date(run.started_at).toLocaleString() : '-'}</TableCell>
                              <TableCell>{run.finished_at ? new Date(run.finished_at).toLocaleString() : '-'}</TableCell>
                              <TableCell>
                                {run.result ? `Total: ${run.result.total} Pass: ${run.result.pass_} Fail: ${run.result.fail}` : '-'}
                              </TableCell>
                              <TableCell className="max-w-[120px] truncate">{run.trace_id || '-'}</TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </TabsContent>
                <TabsContent value="result" className="mt-3">
                  {detail.last_result ? (
                    <Card size="sm">
                      <CardContent>
                        <pre className="whitespace-pre-wrap m-0 text-xs">
                          {typeof detail.last_result === 'string' ? detail.last_result : JSON.stringify(detail.last_result, null, 2)}
                        </pre>
                      </CardContent>
                    </Card>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-8">暂无结果</p>
                  )}
                </TabsContent>
              </Tabs>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Run Detail Dialog */}
      <Dialog open={runDetailOpen} onOpenChange={(open) => { if (!open) { setRunDetailOpen(false); setSelectedRun(null); setRunArtifacts([]) } }}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              运行详情 #{selectedRun?.id}
              {selectedRun && (
                <Badge tone="neutral" className={statusBadgeClass(RUN_STATUS_MAP[selectedRun.status]?.color)}>
                  {RUN_STATUS_MAP[selectedRun.status]?.label || selectedRun.status}
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          {runDetailLoading && !selectedRun ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="size-6 animate-spin" />
            </div>
          ) : selectedRun ? (
            <div className="flex flex-col gap-4">
              {/* Info grid */}
              <dl className="grid grid-cols-2 border rounded-lg">
                {[
                  ['状态', <Badge key="st" tone="neutral" className={statusBadgeClass(RUN_STATUS_MAP[selectedRun.status]?.color)}>{RUN_STATUS_MAP[selectedRun.status]?.label || selectedRun.status}</Badge>],
                  ['浏览器', selectedRun.browser ? <Badge key="br" tone="neutral" className={browserBadgeClass(BROWSER_MAP[selectedRun.browser]?.color)}><Monitor className="size-3" />{selectedRun.browser}</Badge> : '-'],
                  ['Base URL', selectedRun.base_url || '-'],
                  ['耗时', selectedRun.duration != null ? `${selectedRun.duration}s` : '-'],
                  ['开始时间', selectedRun.started_at ? new Date(selectedRun.started_at).toLocaleString() : '-'],
                  ['结束时间', selectedRun.finished_at ? new Date(selectedRun.finished_at).toLocaleString() : '-'],
                  ['进程 ID', selectedRun.process_id != null ? String(selectedRun.process_id) : '-'],
                ].map(([label, value], i) => (
                  <div key={i} className={`flex flex-col border-b border-r p-2 even:border-r-0 ${i >= 6 ? 'border-b-0' : ''}`}>
                    <dt className="text-xs text-muted-foreground">{label}</dt>
                    <dd className="text-sm mt-0.5 break-all">{value}</dd>
                  </div>
                ))}
              </dl>

              {/* Error message */}
              {selectedRun.error_message && (
                <div className="rounded-lg border border-status-danger-border bg-status-danger-muted p-3 dark:border-status-danger-border dark:bg-status-danger-muted">
                  <div className="flex items-center gap-2 text-sm font-medium text-status-danger dark:text-status-danger">
                    <AlertTriangle className="size-4" />
                    错误信息
                  </div>
                  <pre className="mt-1 whitespace-pre-wrap text-xs text-status-danger dark:text-status-danger">{selectedRun.error_message}</pre>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2 flex-wrap">
                {(selectedRun.status === 'pending' || selectedRun.status === 'running') && (
                  <Button variant="secondary" size="sm" onClick={handleCancelRun} className="text-destructive border-destructive/20 hover:bg-destructive/10">
                    <Ban className="size-4" />
                    取消运行
                  </Button>
                )}
                {selectedRun.status !== 'pending' && selectedRun.status !== 'running' && (
                  <Button variant="secondary" size="sm" onClick={() => { setRunDetailLoading(true); fetchRunDetail(selectedRun.id).then(setSelectedRun).finally(() => setRunDetailLoading(false)); fetchRunArtifacts(selectedRun.id).then(setRunArtifacts).catch(() => {}) }}>
                    <RotateCcw className="size-4" />
                    刷新
                  </Button>
                )}
              </div>

              {/* Result summary */}
              {selectedRun.result && (selectedRun.result.total != null) && (
                <div className="flex gap-3 flex-wrap">
                  <div className="rounded-lg border px-3 py-2 text-center min-w-[70px]">
                    <div className="text-xs text-muted-foreground">总计</div>
                    <div className="text-lg font-semibold">{selectedRun.result.total}</div>
                  </div>
                  <div className="rounded-lg border border-status-success-border bg-status-success-muted px-3 py-2 text-center min-w-[70px] dark:border-status-success-border dark:bg-status-success-muted">
                    <div className="text-xs text-status-success dark:text-status-success">通过</div>
                    <div className="text-lg font-semibold text-status-success dark:text-status-success">{selectedRun.result.pass_ ?? '-'}</div>
                  </div>
                  <div className="rounded-lg border border-status-danger-border bg-status-danger-muted px-3 py-2 text-center min-w-[70px] dark:border-status-danger-border dark:bg-status-danger-muted">
                    <div className="text-xs text-status-danger dark:text-status-danger">失败</div>
                    <div className="text-lg font-semibold text-status-danger dark:text-status-danger">{selectedRun.result.fail ?? '-'}</div>
                  </div>
                  <div className="rounded-lg border px-3 py-2 text-center min-w-[70px]">
                    <div className="text-xs text-muted-foreground">跳过</div>
                    <div className="text-lg font-semibold">{selectedRun.result.skip ?? '-'}</div>
                  </div>
                </div>
              )}

              {/* Stdout/Stderr toggle */}
              <Tabs defaultValue="">
                <TabsList>
                  <TabsTrigger value="" disabled>输出</TabsTrigger>
                  {(selectedRun.stdout) && <TabsTrigger value="stdout"><Terminal className="size-3" />stdout</TabsTrigger>}
                  {(selectedRun.stderr) && <TabsTrigger value="stderr"><XCircle className="size-3" />stderr</TabsTrigger>}
                </TabsList>
                {selectedRun.stdout && (
                  <TabsContent value="stdout" className="mt-3">
                    <Card size="sm">
                      <CardContent>
                        <pre className="whitespace-pre-wrap m-0 text-xs max-h-[300px] overflow-y-auto font-mono">{selectedRun.stdout}</pre>
                      </CardContent>
                    </Card>
                  </TabsContent>
                )}
                {selectedRun.stderr && (
                  <TabsContent value="stderr" className="mt-3">
                    <Card size="sm">
                      <CardContent>
                        <pre className="whitespace-pre-wrap m-0 text-xs max-h-[300px] overflow-y-auto font-mono text-status-danger dark:text-status-danger">{selectedRun.stderr}</pre>
                      </CardContent>
                    </Card>
                  </TabsContent>
                )}
              </Tabs>

              {/* Artifacts */}
              {runArtifacts.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium flex items-center gap-2">
                    <FileText className="size-4" />
                    产物 ({runArtifacts.length})
                  </h4>
                  {/* Screenshots */}
                  {runArtifacts.filter(a => a.type === 'png').length > 0 && (
                    <div>
                      <div className="text-xs text-muted-foreground mb-2 flex items-center gap-1"><Image className="size-3" />截图</div>
                      <div className="grid grid-cols-3 gap-2">
                        {runArtifacts.filter(a => a.type === 'png').slice(0, 9).map((a) => (
                          <a key={a.path} href={`/api/v1/ui-tests/runs/${selectedRun.id}/artifacts/${a.path}`} target="_blank" rel="noreferrer" className="block rounded border overflow-hidden hover:ring-2 hover:ring-primary">
                            <img src={`/api/v1/ui-tests/runs/${selectedRun.id}/artifacts/${a.path}`} alt={a.name} className="w-full h-24 object-cover" />
                            <div className="text-xs p-1 truncate">{a.name}</div>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* Videos */}
                  {runArtifacts.filter(a => a.type === 'webm').map((a) => (
                    <div key={a.path} className="rounded border overflow-hidden">
                      <div className="text-xs text-muted-foreground p-2 flex items-center gap-1"><Video className="size-3" />视频: {a.name}</div>
                      <video controls className="w-full max-h-[300px]" src={`/api/v1/ui-tests/runs/${selectedRun.id}/artifacts/${a.path}`} />
                    </div>
                  ))}
                  {/* Traces */}
                  {runArtifacts.filter(a => a.type === 'zip').map((a) => (
                    <div key={a.path}>
                      <a href={`/api/v1/ui-tests/runs/${selectedRun.id}/artifacts/${a.path}`} className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
                        <Download className="size-3" />
                        下载 Trace: {a.name}
                      </a>
                    </div>
                  ))}
                  {/* Other files */}
                  {runArtifacts.filter(a => !['png', 'webm', 'zip'].includes(a.type)).length > 0 && (
                    <div className="text-xs text-muted-foreground flex flex-wrap gap-2">
                      其他文件:
                      {runArtifacts.filter(a => !['png', 'webm', 'zip'].includes(a.type)).map((a) => (
                        <a key={a.path} href={`/api/v1/ui-tests/runs/${selectedRun.id}/artifacts/${a.path}`} className="text-primary hover:underline">{a.name}</a>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* HTML Report link */}
              {selectedRun.html_report_path && (
                <a href={`/api/v1/ui-tests/runs/${selectedRun.id}/artifacts/report/index.html`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
                  <FileText className="size-4" />
                  查看 HTML 报告
                </a>
              )}

              {/* Empty artifacts for pending/running */}
              {runArtifacts.length === 0 && (selectedRun.status === 'pending' || selectedRun.status === 'running') && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-4 justify-center">
                  <Loader2 className="size-4 animate-spin" />
                  运行中，产物将在完成后显示...
                </div>
              )}
              {runArtifacts.length === 0 && selectedRun.status !== 'pending' && selectedRun.status !== 'running' && (
                <p className="text-sm text-muted-foreground text-center py-4">暂无产物文件</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-12">加载失败</p>
          )}

          <DialogFooter>
            <Button variant="secondary" onClick={() => { setRunDetailOpen(false); setSelectedRun(null); setRunArtifacts([]) }}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ── Script Selector ──

function ScriptSelector({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [scripts, setScripts] = useState<string[]>([])
  const [custom, setCustom] = useState(false)

  useAbortableEffect((signal) => {
    fetchScripts(signal)
      .then((rows) => { if (!signal.aborted) setScripts(rows) })
      .catch(() => { if (!signal.aborted) setScripts([]) })
  }, [])

  if (scripts.length === 0 || custom) {
    return (
      <div className="flex gap-2">
        <Input placeholder="tests/login.spec.js" value={value} onChange={(e) => onChange(e.target.value)} />
        {scripts.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => setCustom(false)}>选择</Button>
        )}
      </div>
    )
  }

  return (
    <div className="flex gap-2">
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger><SelectValue placeholder="选择测试脚本" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="">(空)</SelectItem>
          {scripts.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
        </SelectContent>
      </Select>
      <Button variant="ghost" size="sm" onClick={() => setCustom(true)}>自定义</Button>
    </div>
  )
}
