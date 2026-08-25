import { Fragment, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Plus, Edit, Trash2, Zap } from '@/lib/icons'
import { Button } from '@/ui'
import { Input } from '@/ui'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/ui'
import { Card, CardContent } from '@/components/ui/card'
import Pagination from '@/components/Pagination'
import PageHeader from '@/components/PageHeader'
import EmptyState from '@/components/EmptyState'
import { SkeletonText } from '@/components/ui/skeleton'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { useAuthStore } from '@/stores/auth'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
import { fetchPlans } from '@/api/testplan'
import { fetchEnvironments } from '@/api/environment'
import {
  createSchedule,
  deleteSchedule,
  fetchSchedules,
  fetchScheduleRuns,
  triggerSchedule,
  updateSchedule,
} from '@/api/schedule'

const RUN_STATUS_BADGE: Record<string, string> = {
  running: 'bg-status-info-muted text-status-info dark:bg-status-info-muted dark:text-status-info',
  completed: 'bg-status-success-muted text-status-success dark:bg-status-success-muted dark:text-status-success',
  failed: 'bg-status-danger-muted text-status-danger dark:bg-status-danger-muted dark:text-status-danger',
}

const scheduleSchema = z.object({
  name: z.string().min(1, '请输入名称'),
  job_type: z.enum(['plan', 'report']).default('plan'),
  plan_id: z.string({ required_error: '请选择计划' }).min(1, '请选择计划'),
  cron_expression: z.string().min(1, '请输入 Cron 表达式'),
  enabled: z.boolean().default(true),
  description: z.string().optional(),
  disabled_reason: z.string().optional().or(z.literal('')),
  environment_id: z.string().optional().or(z.literal('')),
})

type ScheduleFormValues = z.infer<typeof scheduleSchema>

export default function SchedulePage() {
  useDocumentTitle('定时任务')
  const hasPerm = useAuthStore((state) => state.hasPerm)
  const canCreate = hasPerm('schedule:create')
  const canUpdate = hasPerm('schedule:update')
  const canDelete = hasPerm('schedule:delete')
  const canTrigger = hasPerm('schedule:trigger')
  const [page, setPage] = useState(1)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [plans, setPlans] = useState<any[]>([])
  const [environments, setEnvironments] = useState<any[]>([])
  const [expandedRows, setExpandedRows] = useState<Record<number, { loading: boolean; runs: any[]; total: number }>>({})

  const { data, isLoading, isError, error, refetch } = useApi<any>(
    () => fetchSchedules({ page, page_size: 20 }),
    [page],
  )

  // Batch 163 / C162-2：挂载即加载环境，列表「执行环境」列显示真实名称（不再回退「环境#N」）
  useEffect(() => { loadEnvironments() }, [])

  const form = useForm<ScheduleFormValues>({
    resolver: zodResolver(scheduleSchema),
    defaultValues: { job_type: 'plan', plan_id: '', enabled: true, description: '', disabled_reason: '' },
  })

  const loadPlans = async () => {
    try {
      const r: any = await fetchPlans({ page_size: 200 })
      setPlans(r.items || [])
    } catch {
      setPlans([])
    }
  }

  const loadEnvironments = async () => {
    try {
      const r: any = await fetchEnvironments()
      setEnvironments(r || [])
    } catch {
      setEnvironments([])
    }
  }

  const envName = (id: any) => {
    const e = environments.find((x: any) => String(x.id) === String(id))
    return e?.name || (id ? `环境#${id}` : '')
  }

  const openNew = () => {
    loadPlans()
    loadEnvironments()
    setEditing(null)
    form.reset({ job_type: 'plan', plan_id: '', enabled: true, description: '', disabled_reason: '', environment_id: '' })
    setDrawerOpen(true)
  }

  const openEdit = (row: any) => {
    loadPlans()
    setEditing(row)
    form.reset({
      name: row.name || '',
      job_type: row.job_type === 'report' ? 'report' : 'plan',
      plan_id: row.plan_id != null ? String(row.plan_id) : '',
      cron_expression: row.cron_expression || '',
      enabled: row.enabled ?? true,
      description: row.description || '',
      disabled_reason: row.disabled_reason || '',
      environment_id: row.environment_id != null ? String(row.environment_id) : '',
    })
    setDrawerOpen(true)
  }

  const doSave = async (v: ScheduleFormValues) => {
    setSaving(true)
    try {
      const payload = {
        ...v,
        job_type: v.job_type,
        plan_id: Number(v.plan_id),
        environment_id: v.environment_id ? Number(v.environment_id) : null,
      }
      if (editing?.id) {
        await updateSchedule(editing.id, payload)
        toast.success('已更新')
      } else {
        await createSchedule(payload)
        toast.success('已创建')
      }
      setDrawerOpen(false)
      refetch()
    } finally { setSaving(false) }
  }

  const doDelete = async (id: number) => {
    await deleteSchedule(id)
    toast.success('已删除')
    refetch()
  }

  const [disableTarget, setDisableTarget] = useState<any | null>(null)
  const [disableReason, setDisableReason] = useState('')

  const doToggle = async (id: number, enabled: boolean) => {
    if (!enabled) {
      const row = (data?.items || []).find((r: any) => r.id === id)
      setDisableTarget(row || { id })
      setDisableReason('')
      return
    }
    await updateSchedule(id, { enabled: true, disabled_reason: '' })
    refetch()
  }

  const confirmDisable = async () => {
    if (!disableTarget) return
    if (!disableReason.trim()) {
      toast.error('请填写停用原因')
      return
    }
    await updateSchedule(disableTarget.id, { enabled: false, disabled_reason: disableReason.trim() })
    setDisableTarget(null)
    toast.success('已停用调度')
    refetch()
  }

  const doTrigger = async (id: number) => {
    await triggerSchedule(id)
    toast.success('已触发执行')
    refetch()
  }

  const loadRuns = async (scheduleId: number) => {
    const prev = expandedRows[scheduleId]
    if (prev && prev.runs.length > 0) {
      // collapse
      setExpandedRows((s) => { const n = { ...s }; delete n[scheduleId]; return n })
      return
    }
    setExpandedRows((s) => ({ ...s, [scheduleId]: { loading: true, runs: [], total: 0 } }))
    try {
      const r: any = await fetchScheduleRuns(scheduleId)
      setExpandedRows((s) => ({
        ...s,
        [scheduleId]: { loading: false, runs: r.items || [], total: r.total || 0 },
      }))
    } catch {
      setExpandedRows((s) => ({ ...s, [scheduleId]: { loading: false, runs: [], total: 0 } }))
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader title="定时任务" />

      <Card>
        <CardContent className="flex items-center gap-3 pt-4">
          {canCreate && (
          <Button className="min-h-11" onClick={openNew} data-icon="inline-start">
              <Plus />
              新建调度
            </Button>
          )}
          <span className="text-xs text-muted-foreground">
            示例: <code className="rounded bg-muted px-1.5 py-0.5 text-xs">0 9 * * 1-5</code> 工作日9点, <code className="rounded bg-muted px-1.5 py-0.5 text-xs">0 */4 * * *</code> 每4小时
          </span>
        </CardContent>
      </Card>

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={data}
        onRetry={refetch}
        loadingVariant="skeleton"
        skeletonType="table"
        loadingRows={5}
        emptyTitle="暂无定时任务"
        emptyDescription="点击「新建调度」创建定时测试任务"
        emptyAction={canCreate ? { label: '新建调度', onClick: openNew } : undefined}
      >
        {(d) => {
          if (d.items.length === 0) {
            return (
              <EmptyState
                title="暂无定时任务"
                description="点击「新建调度」创建定时测试任务"
                action={canCreate ? { label: '新建调度', onClick: openNew } : undefined}
              />
            )
          }
          const totalPages = Math.max(1, Math.ceil(d.total / d.page_size))
          return (
            <>
              <div className="rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead className="w-[150px]">目标计划</TableHead>
                      <TableHead className="w-[160px]">Cron 表达式</TableHead>
                      <TableHead className="w-[110px]">执行环境</TableHead>
                      <TableHead className="w-[60px] text-center">启用</TableHead>
                      <TableHead className="w-[160px]">上次执行</TableHead>
                      <TableHead className="w-[200px]">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {d.items.map((row: any) => {
                      const isExpanded = expandedRows[row.id] && expandedRows[row.id].runs.length > 0
                      const expState = expandedRows[row.id]
                      return (
                        <Fragment key={row.id}>
                          <TableRow key={row.id}>
                            <TableCell>
                              <button
                                onClick={() => loadRuns(row.id)}
                                className="text-primary hover:underline text-left"
                              >
                                {row.name}
                              </button>
                              {!row.enabled && row.disabled_reason && (
                                <p className="text-xs text-muted-foreground mt-0.5" title={row.disabled_reason}>
                                  停用原因：{row.disabled_reason}
                                </p>
                              )}
                            </TableCell>
                            <TableCell>
                              {row.plan_name || <span className="text-muted-foreground">—</span>}
                            </TableCell>
                            <TableCell>
                              <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{row.cron_expression}</code>
                            </TableCell>
                            <TableCell>
                              {envName(row.environment_id) || <span className="text-muted-foreground">—</span>}
                            </TableCell>
                            <TableCell className="text-center">
                              <Switch
                                size="sm"
                                checked={row.enabled}
                                disabled={!canUpdate}
                                onCheckedChange={(checked) => doToggle(row.id, checked)}
                                aria-label={`切换调度 ${row.name} 启用状态`}
                              />
                            </TableCell>
                            <TableCell>
                              {row.last_run
                                ? new Date(row.last_run).toLocaleString()
                                : <span className="text-muted-foreground">—</span>}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                {canTrigger && (
            <Button size="sm" variant="secondary" className="min-h-11" onClick={() => doTrigger(row.id)} data-icon="inline-start">
                                    <Zap />
                                    触发
                                  </Button>
                                )}
                                {canUpdate && (
                                  <Button
                                    size="sm"
                                    variant="secondary"
                                    aria-label="编辑"
                                    onClick={() => openEdit(row)}
                                    data-icon="inline-start"
                                  >
                                    <Edit />
                                  </Button>
                                )}
                                {canDelete && (
                                  <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                      <Button size="sm" variant="danger" aria-label="删除" data-icon="inline-start">
                                        <Trash2 />
                                      </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                      <AlertDialogHeader>
                                        <AlertDialogTitle>确定删除？</AlertDialogTitle>
                                        <AlertDialogDescription>
                                          此操作不可撤销。
                                        </AlertDialogDescription>
                                      </AlertDialogHeader>
                                      <AlertDialogFooter>
                                        <AlertDialogCancel>取消</AlertDialogCancel>
                                        <AlertDialogAction onClick={() => doDelete(row.id)}>删除</AlertDialogAction>
                                      </AlertDialogFooter>
                                    </AlertDialogContent>
                                  </AlertDialog>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                          {isExpanded && (
                            <TableRow key={`${row.id}-expanded`}>
                              <TableCell colSpan={6} className="bg-muted/30 p-0">
                                <div className="p-3">
                                  {expState?.loading ? (
                                    <div className="py-4"><SkeletonText lines={3} /></div>
                                  ) : expState?.runs.length === 0 ? (
                                    <EmptyState title="暂无执行记录" className="py-4" />
                                  ) : (
                                    <Table>
                                      <TableHeader>
                                        <TableRow>
                                          <TableHead className="w-[100px]">状态</TableHead>
                                          <TableHead className="w-[170px]">开始时间</TableHead>
                                          <TableHead className="w-[170px]">结束时间</TableHead>
                                          <TableHead className="w-[200px]">结果</TableHead>
                                          <TableHead>错误</TableHead>
                                        </TableRow>
                                      </TableHeader>
                                      <TableBody>
                                        {expState?.runs.map((run: any) => {
                                          const resultParts: string[] = []
                                          if (run.result?.pass_) resultParts.push(`通过${run.result.pass_}`)
                                          if (run.result?.fail) resultParts.push(`失败${run.result.fail}`)
                                          if (run.result?.pending) resultParts.push(`待执行${run.result.pending}`)
                                          return (
                                            <TableRow key={run.id}>
                                              <TableCell>
                                                <Badge className={RUN_STATUS_BADGE[run.status] || ''}>{run.status}</Badge>
                                              </TableCell>
                                              <TableCell>{run.started_at ? new Date(run.started_at).toLocaleString() : '-'}</TableCell>
                                              <TableCell>{run.finished_at ? new Date(run.finished_at).toLocaleString() : '-'}</TableCell>
                                              <TableCell>{resultParts.length > 0 ? resultParts.join(' / ') : '-'}</TableCell>
                                              <TableCell>
                                                {run.error_message
                                                  ? <span className="text-destructive">{run.error_message}</span>
                                                  : '-'}
                                              </TableCell>
                                            </TableRow>
                                          )
                                        })}
                                      </TableBody>
                                    </Table>
                                  )}
                                </div>
                              </TableCell>
                            </TableRow>
                          )}
                        </Fragment>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <Pagination
                page={d.page}
                totalPages={totalPages}
                total={d.total}
                onChange={(p) => setPage(p)}
              />
            </>
          )
        }}
      </AsyncState>

      {/* Create/Edit Dialog */}
      <Dialog open={drawerOpen} onOpenChange={setDrawerOpen}>
        <DialogContent className="sm:max-w-[520px]">
          <DialogHeader>
            <DialogTitle>{editing?.id ? '编辑调度' : '新建调度'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={form.handleSubmit(doSave)} className="flex flex-col gap-4">
            {/* Name */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">
                调度名称 <span className="text-destructive">*</span>
              </label>
              <Input
                placeholder="如：每日回归测试"
                {...form.register('name')}
                aria-invalid={!!form.formState.errors.name}
              />
              {form.formState.errors.name && (
                <p className="text-xs text-destructive mt-1">{form.formState.errors.name.message}</p>
              )}
            </div>

            {/* Job type select（Batch 155 / P2-15） */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">调度类型</label>
              <Select
                value={form.watch('job_type')}
                onValueChange={(v) => form.setValue('job_type', v as 'plan' | 'report', { shouldValidate: true })}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="plan">定时执行计划</SelectItem>
                  <SelectItem value="report">定时生成报告</SelectItem>
                </SelectContent>
              </Select>
              {form.watch('job_type') === 'report' && (
                <p className="text-xs text-muted-foreground mt-1">按计划维度定时生成测试报告并推送通知</p>
              )}
            </div>

            {/* Plan select */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">
                目标计划 <span className="text-destructive">*</span>
              </label>
              <Select
                value={form.watch('plan_id') || undefined}
                onValueChange={(v) => form.setValue('plan_id', v, { shouldValidate: true })}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="选择测试计划" />
                </SelectTrigger>
                <SelectContent>
                  {plans.map((p: any) => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      {p.plan_id || ''} {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {form.formState.errors.plan_id && (
                <p className="text-xs text-destructive mt-1">{form.formState.errors.plan_id.message}</p>
              )}
            </div>

            {/* 执行环境（Batch 162 / C161-2）：API 计划必选 */}
            {form.watch('job_type') === 'plan' && (
              <div>
                <label className="text-sm font-medium mb-1.5 block">
                  执行环境 <span className="text-muted-foreground">（含 API 用例的计划必选）</span>
                </label>
                <Select
                  value={form.watch('environment_id') || undefined}
                  onValueChange={(v) => form.setValue('environment_id', v, { shouldValidate: true })}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="选择执行环境" />
                  </SelectTrigger>
                  <SelectContent>
                    {environments.map((e: any) => (
                      <SelectItem key={e.id} value={String(e.id)}>
                        {e.name}（{e.env_type || ''}）
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Cron expression */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">
                Cron 表达式 <span className="text-destructive">*</span>
              </label>
              <Input
                placeholder="0 9 * * 1-5"
                {...form.register('cron_expression')}
                aria-invalid={!!form.formState.errors.cron_expression}
              />
              <p className="text-xs text-muted-foreground mt-1">
                格式: 分 时 日 月 周 (5字段, 空格分隔)
              </p>
              {form.formState.errors.cron_expression && (
                <p className="text-xs text-destructive mt-1">{form.formState.errors.cron_expression.message}</p>
              )}
            </div>

            {/* Enabled switch */}
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium">启用</label>
              <Switch
                checked={form.watch('enabled')}
                disabled={editing?.id ? !canUpdate : !canCreate}
                onCheckedChange={(v) => form.setValue('enabled', v)}
                aria-label="设置调度启用状态"
              />
            </div>

            {/* Description */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">描述</label>
              <Textarea
                rows={3}
                placeholder="可选"
                {...form.register('description')}
              />
            </div>
          </form>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button
              disabled={saving || (editing?.id ? !canUpdate : !canCreate)}
              onClick={form.handleSubmit(doSave)}
            >
              {saving ? '保存中…' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 停用原因弹窗（Batch 155 / P2-18） */}
      <AlertDialog open={disableTarget !== null} onOpenChange={(open) => { if (!open) setDisableTarget(null) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>停用调度</AlertDialogTitle>
            <AlertDialogDescription>请填写停用原因（必填），用于后续追溯。</AlertDialogDescription>
          </AlertDialogHeader>
          <Textarea
            rows={3}
            value={disableReason}
            onChange={(e) => setDisableReason(e.target.value)}
            placeholder="例如：版本发布后该计划不再适用"
            aria-label="停用原因"
          />
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => void confirmDisable()}>确认停用</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
