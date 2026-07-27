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
import { useCallback, useEffect, useState } from 'react'
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
import type { AvMeasurementItem, AvMeasurementTemplate, AvTaskItem } from '@/types'
import { toast } from 'sonner'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import Pagination from '@/components/Pagination'
import PageHeader from '@/components/PageHeader'
import EmptyState from '@/components/EmptyState'
import { SkeletonText } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
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

const PROTOCOL_MAP: Record<string, { color: string }> = {
  HLS: { color: 'blue' },
  FLV: { color: 'green' },
  WebRTC: { color: 'purple' },
  DASH: { color: 'orange' },
}

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  idle: { color: 'default', label: '待检测' },
  running: { color: 'processing', label: '检测中' },
  done: { color: 'green', label: '已完成' },
  fail: { color: 'red', label: '失败' },
}

function protocolBadgeClass(c: string) {
  const map: Record<string, string> = {
    blue: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400',
    green: 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400',
    purple: 'border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-800 dark:bg-purple-950 dark:text-purple-400',
    orange: 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-400',
  }
  return map[c] ?? ''
}

function statusBadgeClass(c: string) {
  const map: Record<string, string> = {
    default: 'border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-400',
    processing: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400',
    green: 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400',
    red: 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400',
  }
  return map[c] ?? ''
}

const avTaskFormSchema = z.object({
  name: z.string().min(1, '请输入任务名称'),
  stream_url: z.string().optional().default(''),
  protocol: z.string().default('HLS'),
})

type AvTaskFormValues = z.infer<typeof avTaskFormSchema>

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

  const form = useForm<AvTaskFormValues>({
    resolver: zodResolver(avTaskFormSchema),
    defaultValues: { name: '', stream_url: '', protocol: 'HLS' },
  })

  const load = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const params: any = { page, page_size: 20 }
      if (fProtocol) params.protocol = fProtocol
      if (fStatus) params.status = fStatus
      if (fKeyword) params.keyword = fKeyword
      const r: any = await fetchAvTasks(params)
      setData(r)
    } finally { setLoading(false) }
  }, [fProtocol, fStatus, fKeyword])

  useEffect(() => { load() }, [load])

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
    await triggerAvCheck(id)
    toast.success('检测已完成')
    load()
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
      <PageHeader title="音视频检测" />

      {/* Filter bar */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <Select value={fProtocol ?? '__all__'} onValueChange={(v) => setFProtocol(v === '__all__' ? undefined : v)}>
          <SelectTrigger className="w-[130px]">
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
          <Button size="icon-sm" variant="ghost" onClick={() => load()}>
            <Search className="size-4" />
          </Button>
        </div>

        <Button variant="outline" size="default" onClick={() => load()}>
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
                  <EmptyState title="暂无音视频任务" description="点击「新建任务」创建音视频质量检测" className="py-0" />
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="max-w-[160px] truncate">{r.task_id}</TableCell>
                  <TableCell className="max-w-0 truncate">{r.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={protocolBadgeClass(PROTOCOL_MAP[r.protocol]?.color)}>
                      {r.protocol}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[r.status]?.color)}>
                      {STATUS_MAP[r.status]?.label || r.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button size="xs" variant="outline" onClick={() => openDetail(r)}>
                        <Eye className="size-3" />
                        详情
                      </Button>
                      {hasPerm('avcheck:trigger') && (
                        <Button size="xs" variant="outline" onClick={() => doTrigger(r.id)} disabled={r.status === 'running'}>
                          <Play className="size-3" />
                          触发
                        </Button>
                      )}
                      {hasPerm('avcheck:delete') && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button size="xs" variant="outline" className="text-destructive border-destructive/20 hover:bg-destructive/10" onClick={() => setDeleteTarget(r.id)}>
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
            <DialogTitle>新建音视频检测</DialogTitle>
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
              <Button type="button" variant="outline" onClick={() => { setDrawer(false); form.reset() }}>
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
        <SheetContent className="sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle>检测详情</SheetTitle>
          </SheetHeader>
          {detail && (
            <div className="flex flex-col gap-4 mt-4 overflow-y-auto flex-1">
              <dl className="grid grid-cols-2 border rounded-lg">
                {[
                  ['编号', detail.task_id],
                  ['名称', detail.name],
                  ['协议', <Badge key="proto" variant="outline" className={protocolBadgeClass(PROTOCOL_MAP[detail.protocol]?.color)}>{detail.protocol}</Badge>],
                  ['状态', <Badge key="st" variant="outline" className={statusBadgeClass(STATUS_MAP[detail.status]?.color)}>{STATUS_MAP[detail.status]?.label}</Badge>],
                  ['流地址', detail.stream_url || '-'],
                  ['创建时间', detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '-'],
                  ['更新时间', detail.updated_at ? new Date(detail.updated_at).toLocaleString('zh-CN') : '-'],
                ].map(([label, value], i, arr) => {
                  const isLast = i >= arr.length - 1 && arr.length % 2 !== 0
                  return (
                    <div
                      key={label as string}
                      className={`flex flex-col border-b border-r p-2 even:border-r-0 [&:nth-last-child(-n+2)]:border-b-0 ${isLast ? 'col-span-2 border-r-0' : ''}`}
                    >
                      <dt className="text-xs text-muted-foreground">{label}</dt>
                      <dd className="text-sm mt-0.5">{value}</dd>
                    </div>
                  )
                })}
              </dl>

              {/* Metrics */}
              {detail.metrics && detail.metrics.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">检测指标</h4>
                  <div className="grid grid-cols-3 gap-3">
                    {detail.metrics.map((m: any) => (
                      <Card key={m.id} size="sm" className={m.pass_ ? 'border-green-300 dark:border-green-800' : 'border-red-300 dark:border-red-800'}>
                        <CardContent>
                          <div className="flex items-center gap-1.5 mb-1">
                            {m.pass_ ? <CheckCircle2 className="size-4 text-green-500" /> : <XCircle className="size-4 text-red-500" />}
                            <span className="text-xs text-muted-foreground">{m.metric_name}</span>
                          </div>
                          <div className={`text-xl font-bold ${m.pass_ ? 'text-green-600' : 'text-red-600'}`}>
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
                              <Badge variant={m.passed ? 'default' : 'destructive'}>
                                {m.passed ? '达标' : '未达标'}
                              </Badge>
                              <Badge variant="outline">真实样本 {m.sample_count} 个</Badge>
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
                        <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
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
                  <Button onClick={() => { doTrigger(detail.id); setDetailOpen(false) }}>
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
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="text-sm font-medium mb-1 block">指标类型</label>
              <Select value={measurementForm.metric_type} onValueChange={changeMetricType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
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
              <label className="text-sm font-medium mb-1 block">测试场景</label>
              <Input value={measurementForm.scenario} onChange={(e) => setMeasurementForm((p) => ({ ...p, scenario: e.target.value }))} placeholder="如：公司 5GHz WiFi" />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">采集方法</label>
              <Input value={measurementForm.method} onChange={(e) => setMeasurementForm((p) => ({ ...p, method: e.target.value }))} />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">环境</label>
              <Input value={measurementForm.environment} onChange={(e) => setMeasurementForm((p) => ({ ...p, environment: e.target.value }))} placeholder="测试5 / 生产" />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">阈值</label>
              <Input inputMode="decimal" value={measurementForm.threshold} onChange={(e) => setMeasurementForm((p) => ({ ...p, threshold: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <label className="text-sm font-medium mb-1 block">真实样本 *</label>
              <Textarea rows={4} value={measurementForm.samples_text} onChange={(e) => setMeasurementForm((p) => ({ ...p, samples_text: e.target.value }))} placeholder="例如：1200, 1350, 1420；支持逗号、空格或换行分隔" />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">网络条件</label>
              <Input value={measurementForm.network_condition} onChange={(e) => setMeasurementForm((p) => ({ ...p, network_condition: e.target.value }))} placeholder="带宽、延迟、丢包、抖动" />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">设备信息</label>
              <Input value={measurementForm.device_info} onChange={(e) => setMeasurementForm((p) => ({ ...p, device_info: e.target.value }))} placeholder="主播端 / 观众端 / 工具版本" />
            </div>
            <div className="col-span-2">
              <label className="text-sm font-medium mb-1 block">备注</label>
              <Textarea rows={2} value={measurementForm.notes} onChange={(e) => setMeasurementForm((p) => ({ ...p, notes: e.target.value }))} placeholder="异常、正负偏差方向、素材和录制文件说明" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMeasurementOpen(false)}>取消</Button>
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
