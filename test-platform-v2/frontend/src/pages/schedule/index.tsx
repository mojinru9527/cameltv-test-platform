import { Fragment, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Plus, Edit, Trash2, Zap } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import Pagination from '@/components/Pagination'
import PageHeader from '@/components/PageHeader'
import EmptyState from '@/components/EmptyState'
import { SkeletonText } from '@/components/ui/skeleton'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
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
import {
  createSchedule,
  deleteSchedule,
  fetchSchedules,
  fetchScheduleRuns,
  triggerSchedule,
  updateSchedule,
} from '@/api/schedule'

const RUN_STATUS_BADGE: Record<string, string> = {
  running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

const scheduleSchema = z.object({
  name: z.string().min(1, '请输入名称'),
  plan_id: z.string().min(1, '请选择计划'),
  cron_expression: z.string().min(1, '请输入 Cron 表达式'),
  enabled: z.boolean().default(true),
  description: z.string().optional(),
})

type ScheduleFormValues = z.infer<typeof scheduleSchema>

export default function SchedulePage() {
  useDocumentTitle('定时任务')
  const [page, setPage] = useState(1)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [plans, setPlans] = useState<any[]>([])
  const [expandedRows, setExpandedRows] = useState<Record<number, { loading: boolean; runs: any[]; total: number }>>({})

  const { data, isLoading, isError, error, refetch } = useApi<any>(
    () => fetchSchedules({ page, page_size: 20 }),
    [page],
  )

  const form = useForm<ScheduleFormValues>({
    resolver: zodResolver(scheduleSchema),
    defaultValues: { enabled: true, description: '' },
  })

  const loadPlans = async () => {
    try {
      const r: any = await fetchPlans({ page_size: 200 })
      setPlans(r.items || [])
    } catch {
      setPlans([])
    }
  }

  const openNew = () => {
    loadPlans()
    setEditing(null)
    form.reset({ enabled: true, description: '' })
    setDrawerOpen(true)
  }

  const openEdit = (row: any) => {
    loadPlans()
    setEditing(row)
    form.reset({
      name: row.name || '',
      plan_id: row.plan_id != null ? String(row.plan_id) : '',
      cron_expression: row.cron_expression || '',
      enabled: row.enabled ?? true,
      description: row.description || '',
    })
    setDrawerOpen(true)
  }

  const doSave = async (v: ScheduleFormValues) => {
    setSaving(true)
    try {
      const payload = {
        ...v,
        plan_id: Number(v.plan_id),
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

  const doToggle = async (id: number, enabled: boolean) => {
    await updateSchedule(id, { enabled })
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
          <Button onClick={openNew} data-icon="inline-start">
            <Plus />
            新建调度
          </Button>
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
      >
        {(d) => {
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
                            </TableCell>
                            <TableCell>
                              {row.plan_name || <span className="text-muted-foreground">—</span>}
                            </TableCell>
                            <TableCell>
                              <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{row.cron_expression}</code>
                            </TableCell>
                            <TableCell className="text-center">
                              <Switch
                                size="sm"
                                checked={row.enabled}
                                onCheckedChange={(checked) => doToggle(row.id, checked)}
                              />
                            </TableCell>
                            <TableCell>
                              {row.last_run
                                ? new Date(row.last_run).toLocaleString()
                                : <span className="text-muted-foreground">—</span>}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <Button size="sm" variant="outline" onClick={() => doTrigger(row.id)} data-icon="inline-start">
                                  <Zap />
                                  触发
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => openEdit(row)} data-icon="inline-start">
                                  <Edit />
                                </Button>
                                <AlertDialog>
                                  <AlertDialogTrigger asChild>
                                    <Button size="sm" variant="destructive" data-icon="inline-start">
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
                onCheckedChange={(v) => form.setValue('enabled', v)}
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
            <Button variant="outline" onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button disabled={saving} onClick={form.handleSubmit(doSave)}>
              {saving ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
