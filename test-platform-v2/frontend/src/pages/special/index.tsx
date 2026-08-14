import {
  CheckCircle2,
  Eye,
  Play,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  XCircle,
  Loader2,
  Edit,
} from '@/lib/icons'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  createAvMeasurement,
  createAvTask,
  deleteAvMeasurement,
  deleteAvTask,
  fetchAvMeasurementTemplates,
  fetchAvTask,
  fetchAvTasks,
  triggerAvCheck,
  updateAvMeasurement,
  type AvMeasurementPayload,
} from '@/api/avcheck'
import { useAuthStore } from '@/stores/auth'
import useAbortableEffect, { rethrowUnlessAborted } from '@/hooks/useAbortableEffect'
import type { AvMeasurementItem, AvMeasurementTemplate, AvTaskItem } from '@/types'
import { execStatusLabel, normalizeExecStatus } from '@/utils/executionStatus'
import { toast } from 'sonner'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import Pagination from '@/components/Pagination'
import PageHeader from '@/components/PageHeader'
import EmptyState from '@/components/EmptyState'
import { SkeletonText } from '@/components/ui/skeleton'
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export const PROTOCOL_MAP: Record<string, { color: string }> = {
  HLS: { color: 'blue' },
  HTTP: { color: 'blue' },
  HTTPS: { color: 'blue' },
  FLV: { color: 'green' },
  WebRTC: { color: 'purple' },
  DASH: { color: 'orange' },
}

// av_task 状态 → 徽章色（后端词表未迁移，仍为 idle/running/done/fail；筛选 value 保持后端契约值）
// 展示标签统一走 execStatusLabel（共享映射兼容旧值，含义：待执行/执行中/通过/失败）
const STATUS_COLORS: Record<string, string> = {
  idle: 'default',
  running: 'processing',
  done: 'green',
  fail: 'red',
}

function protocolBadgeClass(c: string) {
  const map: Record<string, string> = {
    blue: 'border-status-info-border bg-status-info-muted text-status-info dark:border-status-info-border dark:bg-status-info-muted dark:text-status-info',
    green: 'border-status-success-border bg-status-success-muted text-status-success dark:border-status-success-border dark:bg-status-success-muted dark:text-status-success',
    purple: 'border-status-accent-border bg-status-accent-muted text-status-accent dark:border-status-accent-border dark:bg-status-accent-muted dark:text-status-accent',
    orange: 'border-status-warning-border bg-status-warning-muted text-status-warning dark:border-status-warning-border dark:bg-status-warning-muted dark:text-status-warning',
  }
  return map[c] ?? ''
}

function statusBadgeClass(c: string) {
  const map: Record<string, string> = {
    default: 'border-border bg-muted text-muted-foreground',
    processing: 'border-status-info-border bg-status-info-muted text-status-info dark:border-status-info-border dark:bg-status-info-muted dark:text-status-info',
    green: 'border-status-success-border bg-status-success-muted text-status-success dark:border-status-success-border dark:bg-status-success-muted dark:text-status-success',
    red: 'border-status-danger-border bg-status-danger-muted text-status-danger dark:border-status-danger-border dark:bg-status-danger-muted dark:text-status-danger',
  }
  return map[c] ?? ''
}

const avTaskFormSchema = z.object({
  name: z.string().min(1, '请输入任务名称'),
  stream_url: z.string().optional().default('').refine((v) => !v || /^https?:\/\/.+/.test(v), '请输入有效的 http(s) 流地址'),
  protocol: z.string().default('HLS'),
})

type AvTaskFormValues = z.infer<typeof avTaskFormSchema>

const AV_POLL_INTERVAL_MS = 1000
const AV_POLL_MAX_ATTEMPTS = 60

function waitForNextPoll(signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(resolve, AV_POLL_INTERVAL_MS)
    signal.addEventListener('abort', () => {
      window.clearTimeout(timeout)
      reject(new DOMException('Aborted', 'AbortError'))
    }, { once: true })
  })
}

type MeasurementForm = {
  metric_type: string
  scenario: string
  method: string
  environment: string
  device_info: string
  network_condition: string
  samples_text: string
  threshold: string
  notes: string
}

function emptyMeasurementForm(template?: AvMeasurementTemplate): MeasurementForm {
  return {
    metric_type: template?.metric_type || 'video_delay',
    scenario: '',
    method: template?.method || '',
    environment: '',
    device_info: '',
    network_condition: '',
    samples_text: '',
    threshold: template ? String(template.threshold) : '2000',
    notes: '',
  }
}

export default function SpecialPage() {
  useDocumentTitle('专项测试')
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [data, setData] = useState({ total: 0, items: [] as AvTaskItem[], page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [fProtocol, setFProtocol] = useState<string | undefined>()
  const [fStatus, setFStatus] = useState<string | undefined>()
  const [fKeyword, setFKeyword] = useState('')

  const [drawer, setDrawer] = useState(false)
  const [detail, setDetail] = useState<AvTaskItem | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [measurementOpen, setMeasurementOpen] = useState(false)
  const [measurementSaving, setMeasurementSaving] = useState(false)
  const [measurementTemplates, setMeasurementTemplates] = useState<AvMeasurementTemplate[]>([])
  const [editingMeasurement, setEditingMeasurement] = useState<AvMeasurementItem | null>(null)
  const [measurementForm, setMeasurementForm] = useState<MeasurementForm>(emptyMeasurementForm())
  const [triggeringIds, setTriggeringIds] = useState<Set<number>>(() => new Set())
  const triggerPolls = useRef(new Map<number, AbortController>())

  useEffect(() => () => {
    triggerPolls.current.forEach((controller) => controller.abort())
    triggerPolls.current.clear()
  }, [])

  const form = useForm<AvTaskFormValues>({
    resolver: zodResolver(avTaskFormSchema),
    defaultValues: { name: '', stream_url: '', protocol: 'HLS' },
  })

  const load = useCallback(async (page = 1, signal?: AbortSignal) => {
    setLoading(true)
    try {
      const params: any = { page, page_size: 20 }
      if (fProtocol) params.protocol = fProtocol
      if (fStatus) params.status = fStatus
      if (fKeyword) params.keyword = fKeyword
      const r: any = await fetchAvTasks(params, signal)
      if (!signal?.aborted) setData(r)
    } catch (error) {
      rethrowUnlessAborted(error, signal)
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [fProtocol, fStatus, fKeyword])

  useAbortableEffect((signal) => { void load(1, signal) }, [load])

  const doCreate = async (vals: AvTaskFormValues) => {
    setSaving(true)
    try {
      await createAvTask(vals)
      toast.success('检测任务已创建')
      setDrawer(false)
      form.reset()
      load()
    } finally { setSaving(false) }
  }

  const doTrigger = async (id: number) => {
    if (triggeringIds.has(id)) return

    setTriggeringIds((current) => new Set(current).add(id))
    const controller = new AbortController()
    triggerPolls.current.set(id, controller)
    try {
      const triggered = await triggerAvCheck(id)
      const triggeredStatus = normalizeExecStatus(triggered.status)
      if (triggeredStatus !== 'running') {
        triggeredStatus === 'passed'
          ? toast.success('检测已完成')
          : toast.error('检测失败，请查看任务详情')
        await load()
        return
      }

      toast.info('检测已启动，正在后台执行')
      await load()
      for (let attempt = 0; attempt < AV_POLL_MAX_ATTEMPTS; attempt += 1) {
        const current = await fetchAvTask(id, controller.signal)
        const currentStatus = normalizeExecStatus(current.status)
        if (currentStatus === 'passed' || currentStatus === 'failed') {
          setDetail((openDetail) => openDetail?.id === id ? current : openDetail)
          currentStatus === 'passed'
            ? toast.success('检测已完成')
            : toast.error('检测失败，请查看任务详情')
          await load()
          return
        }
        await waitForNextPoll(controller.signal)
      }
      toast.warning('检测仍在后台执行，可稍后刷新查看')
    } catch (error) {
      if (!(error instanceof DOMException && error.name === 'AbortError')) throw error
    } finally {
      triggerPolls.current.delete(id)
      setTriggeringIds((current) => {
        const next = new Set(current)
        next.delete(id)
        return next
      })
    }
  }

  const doDelete = async () => {
    if (deleteTarget == null) return
    await deleteAvTask(deleteTarget)
    toast.success('已删除')
    setDeleteTarget(null)
    load()
  }

  const openDetail = async (r: AvTaskItem) => {
    try {
      const [detailData, templates]: any[] = await Promise.all([
        fetchAvTask(r.id),
        measurementTemplates.length ? Promise.resolve(measurementTemplates) : fetchAvMeasurementTemplates(),
      ])
      setMeasurementTemplates(templates)
      setDetail(detailData)
      setDetailOpen(true)
    } catch { /* ignore */ }
  }

  const openMeasurement = (measurement?: AvMeasurementItem) => {
    setEditingMeasurement(measurement || null)
    if (measurement) {
      setMeasurementForm({
        metric_type: measurement.metric_type,
        scenario: measurement.scenario,
        method: measurement.method,
        environment: measurement.environment,
        device_info: measurement.device_info,
        network_condition: measurement.network_condition,
        samples_text: measurement.samples.join(', '),
        threshold: String(measurement.threshold),
        notes: measurement.notes,
      })
    } else {
      setMeasurementForm(emptyMeasurementForm(measurementTemplates[0]))
    }
    setMeasurementOpen(true)
  }

  const changeMetricType = (metricType: string) => {
    const template = measurementTemplates.find((item) => item.metric_type === metricType)
    setMeasurementForm((prev) => ({
      ...prev,
      metric_type: metricType,
      method: template?.method || prev.method,
      threshold: template ? String(template.threshold) : prev.threshold,
    }))
  }

  const saveMeasurement = async () => {
    if (!detail) return
    const samples = measurementForm.samples_text
      .split(/[\s,，;；]+/)
      .filter(Boolean)
      .map(Number)
    if (!samples.length || samples.some((item) => !Number.isFinite(item))) {
      toast.error('请输入至少一个有效数值，多个样本用逗号或换行分隔')
      return
    }
    const threshold = Number(measurementForm.threshold)
    if (!Number.isFinite(threshold) || threshold <= 0) {
      toast.error('阈值必须是大于 0 的数值')
      return
    }
    const payload: AvMeasurementPayload = {
      metric_type: measurementForm.metric_type,
      scenario: measurementForm.scenario.trim(),
      method: measurementForm.method.trim(),
      environment: measurementForm.environment.trim(),
      device_info: measurementForm.device_info.trim(),
      network_condition: measurementForm.network_condition.trim(),
      samples,
      threshold,
      notes: measurementForm.notes.trim(),
    }
    setMeasurementSaving(true)
    try {
      if (editingMeasurement) {
        await updateAvMeasurement(detail.id, editingMeasurement.id, payload)
        toast.success('测量记录已更新')
      } else {
        await createAvMeasurement(detail.id, payload)
        toast.success('真实测量结果已保存')
      }
      const refreshed: any = await fetchAvTask(detail.id)
      setDetail(refreshed)
      setMeasurementOpen(false)
      setEditingMeasurement(null)
    } finally {
      setMeasurementSaving(false)
    }
  }

  const removeMeasurement = async (measurementId: number) => {
    if (!detail) return
    await deleteAvMeasurement(detail.id, measurementId)
    const refreshed: any = await fetchAvTask(detail.id)
    setDetail(refreshed)
    toast.success('测量记录已删除')
  }

  return (
    <div className="space-y-4">
      <PageHeader title="专项测试" description="音视频质量检测 + 专项测量（回放/指标判定）" />

      {/* Filter bar */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <Select value={fProtocol ?? '__all__'} onValueChange={(v) => setFProtocol(v === '__all__' ? undefined : v)}>
          <SelectTrigger className="w-[130px]" aria-label="按专项测试协议筛选">
            <SelectValue placeholder="协议" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">全部</SelectItem>
            {Object.keys(PROTOCOL_MAP).map((k) => (
              <SelectItem key={k} value={k}>{k}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={fStatus ?? '__all__'} onValueChange={(v) => setFStatus(v === '__all__' ? undefined : v)}>
          <SelectTrigger className="w-[130px]" aria-label="按专项测试状态筛选">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">全部</SelectItem>
            {Object.keys(STATUS_COLORS).map((k) => (
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
          <Button size="icon-sm" variant="ghost" onClick={() => load()} aria-label="搜索专项测试任务">
            <Search className="size-4" />
          </Button>
        </div>

        <Button variant="secondary" size="md" onClick={() => load()}>
          <RotateCcw className="size-4" />
          刷新
        </Button>
        {hasPerm('avcheck:create') && (
          <Button onClick={() => { form.reset({ name: '', stream_url: '', protocol: 'HLS' }); setDrawer(true) }}>
            <Plus className="size-4" />
            新建检测
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[160px]">编号</TableHead>
              <TableHead>名称</TableHead>
              <TableHead className="w-[100px]">协议</TableHead>
              <TableHead className="w-[100px]">状态</TableHead>
              <TableHead className="w-[170px]">创建时间</TableHead>
              <TableHead className="w-[220px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && data.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-8">
                  <SkeletonText lines={4} />
                </TableCell>
              </TableRow>
            ) : data.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-8">
                <EmptyState title="暂无音视频任务" description="点击「新建检测」创建音视频质量检测" className="py-0" />
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="max-w-[160px] truncate">{r.task_id}</TableCell>
                  <TableCell className="max-w-0 truncate">{r.name}</TableCell>
                  <TableCell>
                    <Badge tone="neutral" className={protocolBadgeClass(PROTOCOL_MAP[r.protocol]?.color)}>
                      {r.protocol}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge tone="neutral" className={statusBadgeClass(STATUS_COLORS[r.status])}>
                      {execStatusLabel(r.status)}
                    </Badge>
                  </TableCell>
                  <TableCell>{r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button size="xs" variant="secondary" onClick={() => openDetail(r)}>
                        <Eye className="size-3" />
                        详情
                      </Button>
                      {hasPerm('avcheck:trigger') && (
                        <Button size="xs" variant="secondary" onClick={() => doTrigger(r.id)} disabled={r.status === 'running' || triggeringIds.has(r.id)}>
                          <Play className="size-3" />
                          触发
                        </Button>
                      )}
                      {hasPerm('avcheck:delete') && (
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
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <Pagination
        page={data.page}
        totalPages={Math.max(1, Math.ceil(data.total / data.page_size))}
        total={data.total}
        onChange={(p) => load(p)}
      />

      {/* Create Dialog */}
      <Dialog open={drawer} onOpenChange={(open) => { if (!open) { setDrawer(false); form.reset() } }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>新建专项检测</DialogTitle>
          </DialogHeader>
          <form onSubmit={form.handleSubmit(doCreate)} className="flex flex-col gap-4">
            <div data-invalid={!!form.formState.errors.name} aria-invalid={!!form.formState.errors.name}>
              <label className="text-sm font-medium mb-1 block">任务名称</label>
              <Input placeholder="如：HLS 直播流检测" {...form.register('name')} />
              {form.formState.errors.name && (
                <p className="text-xs text-destructive mt-0.5">{form.formState.errors.name.message}</p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">流地址</label>
              <Input placeholder="https://example.com/live/stream.m3u8" {...form.register('stream_url')} />
              {form.formState.errors.stream_url && (
                <p className="text-xs text-destructive mt-1">{form.formState.errors.stream_url.message}</p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">协议</label>
              <Select value={form.watch('protocol')} onValueChange={(v) => form.setValue('protocol', v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {['HLS', 'FLV', 'WebRTC', 'DASH'].map((k) => (
                    <SelectItem key={k} value={k}>{k}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <DialogFooter>
              <Button type="button" variant="secondary" onClick={() => { setDrawer(false); form.reset() }}>
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
        <SheetContent className="data-[side=right]:sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle>检测详情</SheetTitle>
          </SheetHeader>
          {detail && (
            <div className="flex flex-col gap-4 mt-4 overflow-y-auto flex-1">
              <dl className="grid grid-cols-1 sm:grid-cols-2 border rounded-lg">
                {[
                  ['编号', detail.task_id],
                  ['名称', detail.name],
                  ['协议', <Badge key="proto" tone="neutral" className={protocolBadgeClass(PROTOCOL_MAP[detail.protocol]?.color)}>{detail.protocol}</Badge>],
                  ['状态', <Badge key="st" tone="neutral" className={statusBadgeClass(STATUS_COLORS[detail.status])}>{execStatusLabel(detail.status)}</Badge>],
                  ['流地址', detail.stream_url || '-'],
                  ['创建时间', detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '-'],
                  ['更新时间', detail.updated_at ? new Date(detail.updated_at).toLocaleString('zh-CN') : '-'],
                ].map(([label, value], i, arr) => {
                  const isLast = i >= arr.length - 1 && arr.length % 2 !== 0
                  return (
                    <div
                      key={label as string}
                      className={`flex min-w-0 flex-col border-b border-r p-2 even:border-r-0 [&:nth-last-child(-n+2)]:border-b-0 ${isLast ? 'col-span-2 border-r-0' : ''}`}
                    >
                      <dt className="text-xs text-muted-foreground">{label}</dt>
                      <dd className="mt-0.5 min-w-0 break-all text-sm">{value}</dd>
                    </div>
                  )
                })}
              </dl>

              {/* Metrics */}
              {detail.metrics && detail.metrics.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">检测指标</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {detail.metrics.map((m: any) => (
                      <Card key={m.id} size="sm" className={m.pass_ ? 'border-status-success-border dark:border-status-success-border' : 'border-status-danger-border dark:border-status-danger-border'}>
                        <CardContent>
                          <div className="flex items-center gap-1.5 mb-1">
                            {m.pass_ ? <CheckCircle2 className="size-4 text-status-success" /> : <XCircle className="size-4 text-status-danger" />}
                            <span className="text-xs text-muted-foreground">{m.metric_name}</span>
                          </div>
                          <div className={`text-xl font-bold ${m.pass_ ? 'text-status-success' : 'text-status-danger'}`}>
                            {m.metric_value}
                            <span className="text-xs font-normal text-muted-foreground ml-1">/ &le; {m.threshold}</span>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}

              <div className="rounded-lg border p-3 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-medium">专项测量记录</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      录入采集器、OCR、录屏解帧或 ffprobe 得到的真实样本，平台自动统计，不生成模拟数据。
                    </p>
                  </div>
                  {hasPerm('avcheck:create') && (
                    <Button size="sm" onClick={() => openMeasurement()}>
                      <Plus className="size-4" />
                      录入测量
                    </Button>
                  )}
                </div>

                {(!detail.measurements || detail.measurements.length === 0) ? (
                  <div className="text-sm text-muted-foreground rounded-md bg-muted/40 p-3">
                    暂无真实测量记录。可按“视频延迟、连麦延迟、音画同步、帧率、首帧耗时”模板录入。
                  </div>
                ) : (
                  <div className="space-y-2">
                    {detail.measurements.map((m) => (
                      <div key={m.id} className="rounded-md border p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium">{m.metric_name}</span>
                              <Badge tone={m.passed ? 'success' : 'danger'}>
                                {m.passed ? '达标' : '未达标'}
                              </Badge>
                              <Badge tone="neutral">真实样本 {m.sample_count} 个</Badge>
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">
                              {m.scenario || '未填写场景'} · {m.method || '未填写方法'}
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            {hasPerm('avcheck:create') && (
                              <Button size="xs" variant="ghost" onClick={() => openMeasurement(m)} aria-label="编辑测量记录">
                                <Edit className="size-3" />
                              </Button>
                            )}
                            {hasPerm('avcheck:delete') && (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button size="xs" variant="ghost" aria-label="删除测量记录">
                                    <Trash2 className="size-3 text-destructive" />
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>删除这条测量记录？</AlertDialogTitle>
                                    <AlertDialogDescription>只删除本条真实样本统计，不删除专项任务。</AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>取消</AlertDialogCancel>
                                    <AlertDialogAction variant="destructive" onClick={() => removeMeasurement(m.id)}>删除</AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            )}
                          </div>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-3 text-xs">
                          <div className="rounded bg-muted/40 p-2">平均值 <strong>{m.mean} {m.unit}</strong></div>
                          <div className="rounded bg-muted/40 p-2">P95 <strong>{m.p95} {m.unit}</strong></div>
                          <div className="rounded bg-muted/40 p-2">最大值 <strong>{m.max} {m.unit}</strong></div>
                          <div className="rounded bg-muted/40 p-2">最小值 <strong>{m.min} {m.unit}</strong></div>
                          <div className="rounded bg-muted/40 p-2">标准差 <strong>{m.stddev}</strong></div>
                          <div className="rounded bg-muted/40 p-2">
                            判定 {m.pass_basis.toUpperCase()} {m.comparator} {m.threshold} {m.unit}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {detail.status === 'idle' && hasPerm('avcheck:trigger') && (
                <div className="text-center pt-2">
                  <Button
                    disabled={triggeringIds.has(detail.id)}
                    onClick={() => { doTrigger(detail.id); setDetailOpen(false) }}
                  >
                    <Play className="size-4" />
                    开始检测
                  </Button>
                </div>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>

      <Dialog open={measurementOpen} onOpenChange={(open) => { if (!open) { setMeasurementOpen(false); setEditingMeasurement(null) } }}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingMeasurement ? '编辑专项测量' : '录入专项测量'}</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label htmlFor="measurement-metric-type" className="text-sm font-medium mb-1 block">指标类型</label>
              <Select value={measurementForm.metric_type} onValueChange={changeMetricType}>
                <SelectTrigger id="measurement-metric-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {measurementTemplates.map((item) => (
                    <SelectItem key={item.metric_type} value={item.metric_type}>{item.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {measurementTemplates.find((item) => item.metric_type === measurementForm.metric_type)?.preconditions?.length ? (
                <ul className="mt-2 text-xs text-muted-foreground list-disc pl-5 space-y-0.5">
                  {measurementTemplates.find((item) => item.metric_type === measurementForm.metric_type)!.preconditions.map((item) => <li key={item}>{item}</li>)}
                </ul>
              ) : null}
            </div>
            <div>
              <label htmlFor="measurement-scenario" className="text-sm font-medium mb-1 block">测试场景</label>
              <Input id="measurement-scenario" value={measurementForm.scenario} onChange={(e) => setMeasurementForm((p) => ({ ...p, scenario: e.target.value }))} placeholder="如：公司 5GHz WiFi" />
            </div>
            <div>
              <label htmlFor="measurement-method" className="text-sm font-medium mb-1 block">采集方法</label>
              <Input id="measurement-method" value={measurementForm.method} onChange={(e) => setMeasurementForm((p) => ({ ...p, method: e.target.value }))} />
            </div>
            <div>
              <label htmlFor="measurement-environment" className="text-sm font-medium mb-1 block">环境</label>
              <Input id="measurement-environment" value={measurementForm.environment} onChange={(e) => setMeasurementForm((p) => ({ ...p, environment: e.target.value }))} placeholder="测试5 / 生产" />
            </div>
            <div>
              <label htmlFor="measurement-threshold" className="text-sm font-medium mb-1 block">阈值</label>
              <Input id="measurement-threshold" inputMode="decimal" value={measurementForm.threshold} onChange={(e) => setMeasurementForm((p) => ({ ...p, threshold: e.target.value }))} />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="measurement-samples" className="text-sm font-medium mb-1 block">真实样本 *</label>
              <Textarea id="measurement-samples" rows={4} value={measurementForm.samples_text} onChange={(e) => setMeasurementForm((p) => ({ ...p, samples_text: e.target.value }))} placeholder="例如：1200, 1350, 1420；支持逗号、空格或换行分隔" />
            </div>
            <div>
              <label htmlFor="measurement-network" className="text-sm font-medium mb-1 block">网络条件</label>
              <Input id="measurement-network" value={measurementForm.network_condition} onChange={(e) => setMeasurementForm((p) => ({ ...p, network_condition: e.target.value }))} placeholder="带宽、延迟、丢包、抖动" />
            </div>
            <div>
              <label htmlFor="measurement-device" className="text-sm font-medium mb-1 block">设备信息</label>
              <Input id="measurement-device" value={measurementForm.device_info} onChange={(e) => setMeasurementForm((p) => ({ ...p, device_info: e.target.value }))} placeholder="主播端 / 观众端 / 工具版本" />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="measurement-notes" className="text-sm font-medium mb-1 block">备注</label>
              <Textarea id="measurement-notes" rows={2} value={measurementForm.notes} onChange={(e) => setMeasurementForm((p) => ({ ...p, notes: e.target.value }))} placeholder="异常、正负偏差方向、素材和录制文件说明" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setMeasurementOpen(false)}>取消</Button>
            <Button onClick={saveMeasurement} disabled={measurementSaving}>
              {measurementSaving && <Loader2 className="size-4 animate-spin" />}
              保存并统计
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
