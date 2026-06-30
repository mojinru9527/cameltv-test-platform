import { Fragment, useCallback, useEffect, useState } from 'react'
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
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from '@/components/ui/sheet'
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
  const [data, setData] = useState({ total: 0, items: [] as any[], page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [plans, setPlans] = useState<any[]>([])
  const [expandedRows, setExpandedRows] = useState<Record<number, { loading: boolean; runs: any[]; total: number }>>({})

  const form = useForm<ScheduleFormValues>({
    resolver: zodResolver(scheduleSchema),
    defaultValues: { enabled: true, description: '' },
  })

  const load = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const r: any = await fetchSchedules({ page, page_size: 20 })
      setData(r)
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const loadPlans = async () => {
    try {
      const r: any = await fetchPlans({ page_size: 200 })
      setPlans(r.items || [])
    } catch { /* */ }
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
      load()
    } finally { setSaving(false) }
  }

  const doDelete = async (id: number) => {
    await deleteSchedule(id)
    toast.success('已删除')
    load()
  }

  const doToggle = async (id: number, enabled: boolean) => {
    await updateSchedule(id, { enabled })
    load()
  }

  const doTrigger = async (id: number) => {
    await triggerSchedule(id)
    toast.success('已触发执行')
    load()
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

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size))

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">定时任务</h2>

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
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  加载中...
                </TableCell>
              </TableRow>
            ) : data.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((row: any) => {
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
                              <div className="text-center text-sm text-muted-foreground py-4">加载中...</div>
                            ) : expState?.runs.length === 0 ? (
                              <div className="text-center text-sm text-muted-foreground py-4">暂无执行记录</div>
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
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {data.total > 0 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>共 {data.total} 条</span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={data.page <= 1}
              onClick={() => load(data.page - 1)}
            >
              上一页
            </Button>
            <span>{data.page} / {totalPages}</span>
            <Button
              variant="outline"
              size="sm"
              disabled={data.page >= totalPages}
              onClick={() => load(data.page + 1)}
            >
              下一页
            </Button>
          </div>
        </div>
      )}

      {/* Create/Edit Sheet */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="w-[520px] sm:max-w-[520px]">
          <SheetHeader>
            <SheetTitle>{editing?.id ? '编辑调度' : '新建调度'}</SheetTitle>
          </SheetHeader>
          <form onSubmit={form.handleSubmit(doSave)} className="flex flex-col gap-4 flex-1 overflow-y-auto py-4">
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
          <SheetFooter>
            <Button variant="outline" onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button disabled={saving} onClick={form.handleSubmit(doSave)}>
              {saving ? '保存中...' : '保存'}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  )
}
