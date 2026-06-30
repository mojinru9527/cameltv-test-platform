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
} from '@/lib/icons'
import { useCallback, useEffect, useState } from 'react'
import { createAvTask, deleteAvTask, fetchAvTask, fetchAvTasks, triggerAvCheck } from '@/api/avcheck'
import { useAuthStore } from '@/stores/auth'
import type { AvTaskItem } from '@/types'
import { toast } from 'sonner'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
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

export default function SpecialPage() {
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
      const detailData: any = await fetchAvTask(r.id)
      setDetail(detailData)
      setDetailOpen(true)
    } catch { /* ignore */ }
  }

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size))

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold tracking-tight">音视频检测</h2>

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
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  <Loader2 className="size-4 inline animate-spin mr-2" />
                  加载中...
                </TableCell>
              </TableRow>
            ) : data.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  暂无数据
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
      {data.total > 0 && (
        <div className="flex items-center justify-between mt-4 text-sm text-muted-foreground">
          <span>共 {data.total} 条</span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" disabled={data.page <= 1} onClick={() => load(data.page - 1)}>
              上一页
            </Button>
            <span>{data.page} / {totalPages}</span>
            <Button variant="outline" size="sm" disabled={data.page >= totalPages} onClick={() => load(data.page + 1)}>
              下一页
            </Button>
          </div>
        </div>
      )}

      {/* Create Sheet */}
      <Sheet open={drawer} onOpenChange={(open) => { if (!open) { setDrawer(false); form.reset() } }}>
        <SheetContent className="sm:max-w-md">
          <SheetHeader>
            <SheetTitle>新建音视频检测</SheetTitle>
          </SheetHeader>
          <form onSubmit={form.handleSubmit(doCreate)} className="flex flex-col gap-4 mt-4 overflow-y-auto flex-1">
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

            <SheetFooter>
              <Button type="button" variant="outline" onClick={() => { setDrawer(false); form.reset() }}>
                取消
              </Button>
              <Button type="submit" disabled={saving}>
                {saving && <Loader2 className="size-4 animate-spin" />}
                保存
              </Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>

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
    </div>
  )
}
