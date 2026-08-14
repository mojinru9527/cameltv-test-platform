import {
  Edit,
  Eye,
  Monitor,
  Play,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  FileText,
} from '@/lib/icons'
import { useCallback, useEffect, useState } from 'react'
import { createUiJob, deleteUiJob, fetchUiJob, fetchUiJobs, fetchUiRuns, triggerUiJob, updateUiJob, fetchScripts, fetchRunDetail, cancelRun, fetchRunArtifacts } from '@/api/uitest'
import { fetchEnvironments } from '@/api/environment'
import { fetchTestCases } from '@/api/testcase'
import { useAuthStore } from '@/stores/auth'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import type { Environment, UiJobItem, UiRunItem, UiRunArtifact } from '@/types'
import { toast } from 'sonner'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'

import DataTable, { type DataTableColumn } from '@/components/DataTable'
import { ErrorState } from '@/components/state'
import PageHeader from '@/components/PageHeader'
import { Button } from '@/ui'
import { Input } from '@/ui'
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
import { execStatusLabel } from '@/utils/executionStatus'
import { BROWSER_MAP, browserBadgeClass, getEnvironment, isProductionJob, statusBadgeClass } from './uiShared'
import UiJobFormDialog, { uiJobFormSchema, type UiJobFormValues } from './components/UiJobFormDialog'
import UiJobDetailSheet from './components/UiJobDetailSheet'
import ProductionTriggerDialog from './components/ProductionTriggerDialog'
import UiRunDetailDialog from './components/UiRunDetailDialog'

export { ProtectedArtifactMedia } from './components/ProtectedArtifactMedia'

export default function UiTestPage() {
  // (batch-165) 用例/脚本资产可见性
  const [pageTab, setPageTab] = useState<'jobs' | 'assets'>('jobs')
  const [uiScripts, setUiScripts] = useState<string[]>([])

  useEffect(() => {
    const controller = new AbortController()
    fetchScripts(controller.signal)
      .then((rows: any) => { if (!controller.signal.aborted) setUiScripts(rows || []) })
      .catch(() => {})
    return () => controller.abort()
  }, [])

  useDocumentTitle('UI 测试')
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [data, setData] = useState({ total: 0, items: [] as UiJobItem[], page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<Error | null>(null)
  const [fStatus, setFStatus] = useState<string | undefined>()
  const [fKeyword, setFKeyword] = useState('')
  const [environments, setEnvironments] = useState<Environment[]>([])
  const [uiCases, setUiCases] = useState<any[]>([])
  const [caseMap, setCaseMap] = useState<Record<number, string>>({})

  useAbortableEffect((signal) => {
    fetchEnvironments(signal)
      .then((rows) => { if (!signal.aborted) setEnvironments(rows) })
      .catch(() => { if (!signal.aborted) setEnvironments([]) })
  }, [])

  useAbortableEffect((signal) => {
    fetchTestCases({ case_type: 'ui', page_size: 200 }, signal)
      .then((d: any) => {
        if (signal.aborted) return
        const items = d?.items || []
        setUiCases(items)
        setCaseMap(Object.fromEntries(items.map((c: any) => [c.id, c.title])))
      })
      .catch(() => { if (!signal.aborted) setUiCases([]) })
  }, [])

  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<UiJobItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [prodTriggerTarget, setProdTriggerTarget] = useState<UiJobItem | null>(null)
  const [triggering, setTriggering] = useState(false)

  const [detail, setDetail] = useState<any>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [runs, setRuns] = useState({ total: 0, items: [] as UiRunItem[] })

  // Run detail state
  const [selectedRun, setSelectedRun] = useState<UiRunItem | null>(null)
  const [runDetailOpen, setRunDetailOpen] = useState(false)
  const [runArtifacts, setRunArtifacts] = useState<UiRunArtifact[]>([])
  const [runDetailLoading, setRunDetailLoading] = useState(false)
  const selectedRunId = selectedRun?.id
  const selectedRunStatus = selectedRun?.status

  // Auto-poll run detail while running/pending
  useEffect(() => {
    if (!selectedRunId || !runDetailOpen) return
    if (selectedRunStatus !== 'pending' && selectedRunStatus !== 'running') return

    // Batch 178（FIX-173-P2-12）：指数退避轮询（1s→2s→4s→8s→10s 封顶），
    // 运行状态变化会重置退避（deps 含 selectedRunStatus）。
    let delay = 1000
    let timer: ReturnType<typeof setTimeout> | null = null
    const schedule = () => {
      timer = setTimeout(async () => {
        try {
          const fresh = await fetchRunDetail(selectedRunId)
          setSelectedRun(fresh)
          if (fresh.status !== 'pending' && fresh.status !== 'running') {
            // Load artifacts when done
            try {
              const arts = await fetchRunArtifacts(selectedRunId)
              setRunArtifacts(arts)
            } catch { /* ignore */ }
          }
        } catch { /* ignore */ }
        delay = Math.min(delay * 2, 10_000)
        schedule()
      }, delay)
    }
    schedule()

    return () => {
      if (timer) clearTimeout(timer)
    }
  }, [selectedRunId, selectedRunStatus, runDetailOpen])

  const form = useForm<UiJobFormValues>({
    resolver: zodResolver(uiJobFormSchema),
    defaultValues: { name: '', description: '', test_spec: '', browser: 'chromium', environment_id: null, case_id: null, cron_expression: '', schedule_enabled: false },
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
    { key: 'case_title', header: '关联用例', headerClassName: 'w-[180px]', className: 'max-w-[180px] truncate', render: (r) => r.case_title || (r.case_id != null ? caseMap[r.case_id] : undefined) || r.case_id || '-' },
    { key: 'test_spec', header: '测试文件', headerClassName: 'w-[200px]', className: 'max-w-[200px] truncate', render: (r) => r.test_spec || '-' },
    { key: 'browser', header: '浏览器', headerClassName: 'w-[100px]', render: (r) => (
      <Badge tone="neutral" className={browserBadgeClass(BROWSER_MAP[r.browser]?.color)}>
        <Monitor className="size-3" />
        {r.browser}
      </Badge>
    )},
    { key: 'environment', header: '目标环境', headerClassName: 'w-[180px]', render: (r) => {
      const environment = getEnvironment(environments, r)
      if (!environment) return <span className="text-muted-foreground">未绑定</span>
      const production = environment.is_production === true || environment.env_type === 'prod'
      return (
        <div className="flex min-w-0 items-center gap-1">
          {production && <Badge tone="danger">PROD</Badge>}
          <span className="truncate" title={`${environment.name} · ${environment.base_url || '未配置 Base URL'}`}>
            {environment.name}
          </span>
        </div>
      )
    }},
    { key: 'status', header: '状态', headerClassName: 'w-[100px]', render: (r) => (
      <Badge tone="neutral" className={statusBadgeClass(r.status)}>
        {execStatusLabel(r.status)}
      </Badge>
    )},
    { key: 'last_run_time', header: '上次执行', headerClassName: 'w-[170px]', render: (r) => r.last_run_time ? new Date(r.last_run_time).toLocaleString('zh-CN') : '-' },
    { key: 'actions', header: '操作', headerClassName: 'w-[240px]', render: (r) => {
      const production = isProductionJob(environments, r)
      const canTriggerTarget = !production || hasPerm('uitest:trigger_prod')
      return <div className="flex items-center gap-1">
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
          <Button
            size="xs"
            variant="secondary"
            onClick={() => requestTrigger(r)}
            disabled={r.status === 'running' || !canTriggerTarget}
            title={!canTriggerTarget ? '缺少 uitest:trigger_prod 生产执行权限' : undefined}
          >
            <Play className="size-3" />
            执行
          </Button>
        )}
        {hasPerm('uitest:delete') && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button size="xs" variant="secondary" className="text-destructive border-destructive/20 hover:bg-destructive/10" onClick={() => setDeleteTarget(r.id)} aria-label={`删除 UI 测试任务 ${r.name}`}>
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
    }},
  ]

  const load = useCallback(async (page = 1, signal?: AbortSignal) => {
    setLoading(true)
    setLoadError(null)
    try {
      const params: any = { page, page_size: 20 }
      if (fStatus) params.status = fStatus
      if (fKeyword) params.keyword = fKeyword
      const r: any = await fetchUiJobs(params, signal)
      if (!signal?.aborted) setData(r)
    } catch (error) {
      if (!signal?.aborted) {
        setLoadError(error instanceof Error ? error : new Error('UI 测试任务加载失败'))
      }
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

  const doTrigger = async (id: number, confirmProd = false) => {
    await triggerUiJob(id, confirmProd)
    toast.success('执行已触发')
    load()
  }

  const requestTrigger = async (job: UiJobItem) => {
    if (isProductionJob(environments, job)) {
      setProdTriggerTarget(job)
      return
    }
    await doTrigger(job.id)
  }

  const confirmProductionTrigger = async () => {
    if (!prodTriggerTarget) return
    setTriggering(true)
    try {
      await doTrigger(prodTriggerTarget.id, true)
      setProdTriggerTarget(null)
    } finally {
      setTriggering(false)
    }
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

  const handleRefreshRunDetail = () => {
    if (!selectedRun) return
    setRunDetailLoading(true)
    fetchRunDetail(selectedRun.id).then(setSelectedRun).finally(() => setRunDetailLoading(false))
    fetchRunArtifacts(selectedRun.id).then(setRunArtifacts).catch(() => {})
  }

  const openEdit = (r: UiJobItem) => {
    setEditing(r)
    form.reset({
      name: r.name ?? '',
      description: r.description ?? '',
      test_spec: r.test_spec ?? '',
      browser: r.browser ?? 'chromium',
      environment_id: r.environment_id ?? null,
      case_id: r.case_id ?? null,
      cron_expression: r.cron_expression ?? '',
      schedule_enabled: r.schedule_enabled ?? false,
    })
    setDrawer(true)
  }

  return (
    <div className="space-y-4">
      <PageHeader title="UI 测试" />

      <Tabs value={pageTab} onValueChange={(v) => setPageTab(v as 'jobs' | 'assets')}>
        <TabsList>
          <TabsTrigger value="jobs">任务 ({data.total})</TabsTrigger>
          <TabsTrigger value="assets">用例 / 脚本</TabsTrigger>
        </TabsList>

        <TabsContent value="jobs" className="mt-3">
      {loadError ? (
        <ErrorState error={loadError} onRetry={() => { void load(data.page) }} />
      ) : (
      <DataTable
        columns={uiJobColumns}
        data={data.items}
        className="[&_[data-slot=table-container]]:overflow-visible"
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
              <SelectTrigger className="w-[130px]" aria-label="按 UI 测试任务状态筛选">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部</SelectItem>
                {(['pending', 'running', 'passed', 'failed'] as const).map((k) => (
                  <SelectItem key={k} value={k}>{execStatusLabel(k)}</SelectItem>
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
              <Button onClick={() => { form.reset({ name: '', description: '', test_spec: '', browser: 'chromium', environment_id: null, case_id: null, cron_expression: '', schedule_enabled: false }); setEditing(null); setDrawer(true) }}>
                <Plus className="size-4" />
                新建任务
              </Button>
            )}
          </div>
        }
      />
      )}

      <UiJobFormDialog
        open={drawer}
        onClose={() => { setDrawer(false); setEditing(null); form.reset() }}
        form={form}
        editing={editing}
        saving={saving}
        environments={environments}
        uiCases={uiCases}
        onSubmit={doSave}
      />

      <UiJobDetailSheet
        open={detailOpen}
        onOpenChange={(open) => { if (!open) { setDetailOpen(false); setDetail(null) } }}
        detail={detail}
        runs={runs}
        environments={environments}
        hasPerm={hasPerm}
        onRequestTrigger={requestTrigger}
        onOpenRunDetail={openRunDetail}
      />

      <ProductionTriggerDialog
        target={prodTriggerTarget}
        triggering={triggering}
        environments={environments}
        onOpenChange={(open) => { if (!open && !triggering) setProdTriggerTarget(null) }}
        onConfirm={confirmProductionTrigger}
      />

      <UiRunDetailDialog
        open={runDetailOpen}
        onOpenChange={(open) => { if (!open) { setRunDetailOpen(false); setSelectedRun(null); setRunArtifacts([]) } }}
        run={selectedRun}
        loading={runDetailLoading}
        artifacts={runArtifacts}
        onCancelRun={handleCancelRun}
        onRefresh={handleRefreshRunDetail}
      />
        </TabsContent>

        <TabsContent value="assets" className="mt-3 space-y-4">
          {/* UI 自动化用例 */}
          <Card>
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">UI 自动化用例</h3>
                <Badge tone="neutral" className="text-xs">{uiCases.length}</Badge>
              </div>
              {uiCases.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  暂无 UI 自动化用例，可在「用例服务」中按 UI 自动化类型创建，再在任务表单里关联。
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>标题</TableHead>
                      <TableHead>模块</TableHead>
                      <TableHead>优先级</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {uiCases.map((c: any) => (
                      <TableRow key={c.id}>
                        <TableCell className="font-medium">{c.title}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{c.module || '-'}</TableCell>
                        <TableCell><Badge tone="neutral" className="text-xs">{c.priority || '-'}</Badge></TableCell>
                        <TableCell className="text-xs text-muted-foreground">{c.review_status || '-'}</TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => { form.reset({ name: `${c.title}-任务`, description: '', test_spec: '', browser: 'chromium', environment_id: null, case_id: c.id, cron_expression: '', schedule_enabled: false }); setEditing(null); setDrawer(true) }}
                          >
                            以此用例新建任务
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* 脚本资产 */}
          <Card>
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">脚本资产（Playwright spec）</h3>
                <Badge tone="neutral" className="text-xs">{uiScripts.length}</Badge>
              </div>
              {uiScripts.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  暂无脚本资产，可在「新建任务」中选择或填写 spec 文件路径。
                </p>
              ) : (
                <ul className="divide-y rounded-md border">
                  {uiScripts.map((s) => (
                    <li key={s} className="flex items-center gap-2 px-3 py-2 text-sm">
                      <FileText className="size-4 shrink-0 text-muted-foreground" />
                      <code className="truncate font-mono text-xs">{s}</code>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
