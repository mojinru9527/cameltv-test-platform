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
} from '@/lib/icons'
import { useCallback, useEffect, useState } from 'react'
import { createUiJob, deleteUiJob, fetchUiJob, fetchUiJobs, fetchUiRuns, triggerUiJob, updateUiJob } from '@/api/uitest'
import { useAuthStore } from '@/stores/auth'
import type { UiJobItem, UiRunItem } from '@/types'
import { toast } from 'sonner'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

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
  running: { color: 'processing', label: '运行中' },
  done: { color: 'green', label: '完成' },
  fail: { color: 'red', label: '失败' },
}

function browserBadgeClass(c: string) {
  const map: Record<string, string> = {
    blue: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400',
    orange: 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-400',
    purple: 'border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-800 dark:bg-purple-950 dark:text-purple-400',
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

const uiJobFormSchema = z.object({
  name: z.string().min(1, '请输入任务名称'),
  description: z.string().optional().default(''),
  test_spec: z.string().optional().default(''),
  browser: z.string().default('chromium'),
})

type UiJobFormValues = z.infer<typeof uiJobFormSchema>

export default function UiTestPage() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [data, setData] = useState({ total: 0, items: [] as UiJobItem[], page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [fStatus, setFStatus] = useState<string | undefined>()
  const [fKeyword, setFKeyword] = useState('')

  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<UiJobItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  const [detail, setDetail] = useState<any>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [runs, setRuns] = useState({ total: 0, items: [] as UiRunItem[] })

  const form = useForm<UiJobFormValues>({
    resolver: zodResolver(uiJobFormSchema),
    defaultValues: { name: '', description: '', test_spec: '', browser: 'chromium' },
  })

  const load = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const params: any = { page, page_size: 20 }
      if (fStatus) params.status = fStatus
      if (fKeyword) params.keyword = fKeyword
      const r: any = await fetchUiJobs(params)
      setData(r)
    } finally { setLoading(false) }
  }, [fStatus, fKeyword])

  useEffect(() => { load() }, [load])

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

  const openEdit = (r: UiJobItem) => {
    setEditing(r)
    form.reset({
      name: r.name ?? '',
      description: r.description ?? '',
      test_spec: r.test_spec ?? '',
      browser: r.browser ?? 'chromium',
    })
    setDrawer(true)
  }

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size))

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold tracking-tight">UI 测试</h2>

      {/* Filter bar */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
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
        {hasPerm('uitest:create') && (
          <Button onClick={() => { form.reset({ name: '', description: '', test_spec: '', browser: 'chromium' }); setEditing(null); setDrawer(true) }}>
            <Plus className="size-4" />
            新建任务
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead>
              <TableHead className="w-[200px]">测试文件</TableHead>
              <TableHead className="w-[100px]">浏览器</TableHead>
              <TableHead className="w-[100px]">状态</TableHead>
              <TableHead className="w-[170px]">上次执行</TableHead>
              <TableHead className="w-[240px]">操作</TableHead>
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
                  <TableCell className="max-w-0">
                    <button
                      className="text-primary hover:underline text-left truncate cursor-pointer bg-transparent border-0 p-0"
                      onClick={() => openDetail(r)}
                    >
                      {r.name}
                    </button>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate">{r.test_spec || '-'}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={browserBadgeClass(BROWSER_MAP[r.browser]?.color)}>
                      <Monitor className="size-3" />
                      {r.browser}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[r.status]?.color)}>
                      {STATUS_MAP[r.status]?.label || r.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{r.last_run_time ? new Date(r.last_run_time).toLocaleString('zh-CN') : '-'}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button size="xs" variant="outline" onClick={() => openDetail(r)}>
                        <Eye className="size-3" />
                        详情
                      </Button>
                      {hasPerm('uitest:update') && (
                        <Button size="xs" variant="outline" onClick={() => openEdit(r)}>
                          <Edit className="size-3" />
                          编辑
                        </Button>
                      )}
                      {hasPerm('uitest:trigger') && (
                        <Button size="xs" variant="outline" onClick={() => doTrigger(r.id)} disabled={r.status === 'running'}>
                          <Play className="size-3" />
                          执行
                        </Button>
                      )}
                      {hasPerm('uitest:delete') && (
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

      {/* Create/Edit Sheet */}
      <Sheet open={drawer} onOpenChange={(open) => { if (!open) { setDrawer(false); setEditing(null); form.reset() } }}>
        <SheetContent className="sm:max-w-md">
          <SheetHeader>
            <SheetTitle>{editing?.id ? '编辑UI测试任务' : '新建UI测试任务'}</SheetTitle>
          </SheetHeader>
          <form onSubmit={form.handleSubmit(doSave)} className="flex flex-col gap-4 mt-4 overflow-y-auto flex-1">
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
              <label className="text-sm font-medium mb-1 block">测试文件路径</label>
              <Input placeholder="tests/home.spec.ts" {...form.register('test_spec')} />
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

            <SheetFooter>
              <Button type="button" variant="outline" onClick={() => { setDrawer(false); setEditing(null); form.reset() }}>
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
        <SheetContent className="sm:max-w-3xl">
          <SheetHeader>
            <SheetTitle>任务详情</SheetTitle>
          </SheetHeader>
          {detail && (
            <div className="flex flex-col gap-4 mt-4 overflow-y-auto flex-1">
              <dl className="grid grid-cols-2 border rounded-lg">
                {[
                  ['名称', detail.name],
                  ['浏览器', <Badge key="br" variant="outline" className={browserBadgeClass(BROWSER_MAP[detail.browser]?.color)}><Monitor className="size-3" />{detail.browser}</Badge>],
                  ['状态', <Badge key="st" variant="outline" className={statusBadgeClass(STATUS_MAP[detail.status]?.color)}>{STATUS_MAP[detail.status]?.label}</Badge>],
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
                            <TableRow key={run.id}>
                              <TableCell>
                                <Badge variant="outline" className={statusBadgeClass(RUN_STATUS_MAP[run.status]?.color)}>
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
    </div>
  )
}
