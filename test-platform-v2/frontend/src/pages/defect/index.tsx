import {
  AlertTriangle,
  Bug,
  CheckCircle2,
  Clock,
  Edit,
  Eye,
  Link2,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  Loader2,
} from '@/lib/icons'
import { useCallback, useEffect, useState } from 'react'
import { createDefect, deleteDefect, fetchDefectStats, fetchDefects, updateDefect } from '@/api/defect'
import { fetchTestCases } from '@/api/testcase'
import { fetchUsers } from '@/api/system'
import { useAuthStore } from '@/stores/auth'
import type { DefectItem } from '@/types'
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
import Pagination from '@/components/Pagination'
import PageHeader from '@/components/PageHeader'
import StatCard from '@/components/StatCard'
import EmptyState from '@/components/EmptyState'
import SearchInput from '@/components/SearchInput'
import { SkeletonTable } from '@/components/ui/skeleton'
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

const SEVERITY_MAP: Record<string, { color: string; label: string }> = {
  P0: { color: 'red', label: 'P0-致命' },
  P1: { color: 'orange', label: 'P1-严重' },
  P2: { color: 'gold', label: 'P2-一般' },
  P3: { color: 'blue', label: 'P3-建议' },
}

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  open: { color: 'red', label: '待处理' },
  in_progress: { color: 'processing', label: '处理中' },
  resolved: { color: 'green', label: '已解决' },
  closed: { color: 'default', label: '已关闭' },
  wontfix: { color: 'default', label: '不修复' },
}

function severityBadgeClass(c: string) {
  const map: Record<string, string> = {
    red: 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400',
    orange: 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-400',
    gold: 'border-yellow-200 bg-yellow-50 text-yellow-700 dark:border-yellow-800 dark:bg-yellow-950 dark:text-yellow-400',
    blue: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400',
  }
  return map[c] ?? ''
}

function statusBadgeClass(c: string) {
  const map: Record<string, string> = {
    red: 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400',
    processing: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-400',
    green: 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400',
    default: 'border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-400',
  }
  return map[c] ?? ''
}

const defectFormSchema = z.object({
  title: z.string().min(1, '请输入标题'),
  description: z.string().optional().default(''),
  severity: z.string().default('P2'),
  status: z.string().optional(),
  assignee_id: z.coerce.number().nullable().optional(),
  case_id: z.coerce.number().nullable().optional(),
  external_id: z.string().optional().default(''),
  external_url: z.string().optional().default(''),
})

type DefectFormValues = z.infer<typeof defectFormSchema>

export default function DefectPage() {
  const hasPerm = useAuthStore((s) => s.hasPerm)
  const [data, setData] = useState({ total: 0, items: [] as DefectItem[], page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState({ total: 0, by_severity: {} as Record<string, number>, by_status: {} as Record<string, number> })

  // filters
  const [fSeverity, setFSeverity] = useState<string | undefined>()
  const [fStatus, setFStatus] = useState<string | undefined>()
  const [fKeyword, setFKeyword] = useState('')

  // sheet / detail
  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<DefectItem | null>(null)
  const [detail, setDetail] = useState<DefectItem | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  // delete confirm
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  const form = useForm<DefectFormValues>({
    resolver: zodResolver(defectFormSchema),
    defaultValues: { title: '', description: '', severity: 'P2', status: undefined, assignee_id: null, case_id: null, external_id: '', external_url: '' },
  })

  // select options
  const [users, setUsers] = useState<any[]>([])
  const [cases, setCases] = useState<any[]>([])

  const load = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const params: any = { page, page_size: 20 }
      if (fSeverity) params.severity = fSeverity
      if (fStatus) params.status = fStatus
      if (fKeyword) params.keyword = fKeyword
      const r: any = await fetchDefects(params)
      setData(r)
    } finally {
      setLoading(false)
    }
  }, [fSeverity, fStatus, fKeyword])

  const loadStats = useCallback(async () => {
    try {
      const r: any = await fetchDefectStats()
      setStats(r)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { load(); loadStats() }, [load, loadStats])

  const openCreate = () => {
    setEditing(null)
    form.reset({ title: '', description: '', severity: 'P2', status: undefined, assignee_id: null, case_id: null, external_id: '', external_url: '' })
    setDrawer(true)
    fetchUsers().then((r: any) => setUsers(r || [])).catch(() => {})
    fetchTestCases({ page_size: 200 }).then((r: any) => setCases(r?.items || [])).catch(() => {})
  }

  const openEdit = (r: DefectItem) => {
    setEditing(r)
    form.reset({
      title: r.title ?? '',
      description: r.description ?? '',
      severity: r.severity ?? 'P2',
      status: r.status,
      assignee_id: r.assignee_id ?? null,
      case_id: r.case_id ?? null,
      external_id: r.external_id ?? '',
      external_url: r.external_url ?? '',
    })
    setDrawer(true)
    fetchUsers().then((u: any) => setUsers(u || [])).catch(() => {})
    fetchTestCases({ page_size: 200 }).then((c: any) => setCases(c?.items || [])).catch(() => {})
  }

  const doSave = async (vals: DefectFormValues) => {
    setSaving(true)
    try {
      if (editing?.id) {
        await updateDefect(editing.id, vals)
        toast.success('缺陷已更新')
      } else {
        await createDefect(vals)
        toast.success('缺陷已创建')
      }
      setDrawer(false)
      load()
      loadStats()
    } finally {
      setSaving(false)
    }
  }

  const doDelete = async () => {
    if (deleteTarget == null) return
    await deleteDefect(deleteTarget)
    toast.success('已删除')
    setDeleteTarget(null)
    load()
    loadStats()
  }

  const openDetail = (r: DefectItem) => { setDetail(r); setDetailOpen(true) }

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size))

  return (
    <div className="space-y-4">
      <PageHeader title="缺陷管理" />

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <StatCard
          icon={Bug}
          label="缺陷总数"
          value={stats.total}
          variant="glass"
        />
        <StatCard
          icon={AlertTriangle}
          label="P0 致命"
          value={stats.by_severity?.P0 || 0}
          trendUp={false}
          variant="glass"
        />
        <StatCard
          icon={Clock}
          label="待处理"
          value={stats.by_status?.open || 0}
          trendUp={false}
          variant="glass"
        />
        <StatCard
          icon={CheckCircle2}
          label="已解决"
          value={(stats.by_status?.resolved || 0) + (stats.by_status?.closed || 0)}
          trendUp={true}
          variant="glass"
        />
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <Select value={fSeverity ?? '__all__'} onValueChange={(v) => setFSeverity(v === '__all__' ? undefined : v)}>
          <SelectTrigger className="w-[130px]">
            <SelectValue placeholder="严重程度" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">全部</SelectItem>
            {Object.entries(SEVERITY_MAP).map(([k, v]) => (
              <SelectItem key={k} value={k}>{v.label}</SelectItem>
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

        <SearchInput
          value={fKeyword}
          onChange={setFKeyword}
          onSearch={() => load()}
          placeholder="搜索缺陷标题"
          inputClassName="w-[220px]"
          clearable
        />

        <Button variant="outline" size="default" onClick={() => load()}>
          <RotateCcw className="size-4" />
          刷新
        </Button>
        {hasPerm('defect:create') && (
          <Button onClick={openCreate} variant="neon">
            <Plus className="size-4" />
            新建缺陷
          </Button>
        )}
      </div>

      {/* Table */}
      {loading && data.items.length === 0 ? (
        <SkeletonTable rows={5} cols={7} />
      ) : data.items.length === 0 ? (
        <EmptyState
          title="暂无缺陷"
          description="当前筛选条件下没有缺陷记录"
        />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[160px]">编号</TableHead>
                <TableHead>标题</TableHead>
                <TableHead className="w-[100px]">状态</TableHead>
                <TableHead className="w-[100px]">处理人</TableHead>
                <TableHead className="w-[150px]">关联用例</TableHead>
                <TableHead className="w-[170px]">创建时间</TableHead>
                <TableHead className="w-[200px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="max-w-[160px] truncate">{r.defect_id}</TableCell>
                  <TableCell className="max-w-0">
                    <div className="flex items-center gap-1.5">
                      <button
                        className="text-primary hover:underline text-left truncate cursor-pointer bg-transparent border-0 p-0"
                        onClick={() => openDetail(r)}
                      >
                        {r.title}
                      </button>
                      <Badge variant="outline" className={severityBadgeClass(SEVERITY_MAP[r.severity]?.color)}>
                        {SEVERITY_MAP[r.severity]?.label || r.severity}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[r.status]?.color)}>
                      {STATUS_MAP[r.status]?.label || r.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-[100px] truncate">{r.assignee_name}</TableCell>
                  <TableCell className="max-w-[150px] truncate">{r.case_title}</TableCell>
                  <TableCell>{r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button size="xs" variant="outline" onClick={() => openDetail(r)}>
                        <Eye className="size-3" />
                        详情
                      </Button>
                      {hasPerm('defect:update') && (
                        <Button size="xs" variant="outline" onClick={() => openEdit(r)}>
                          <Edit className="size-3" />
                          编辑
                        </Button>
                      )}
                      {hasPerm('defect:delete') && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button size="xs" variant="outline" className="text-destructive border-destructive/20 hover:bg-destructive/10" onClick={() => setDeleteTarget(r.id)}>
                              <Trash2 className="size-3" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>确定删除此缺陷？</AlertDialogTitle>
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
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Pagination */}
      <Pagination
        page={data.page}
        totalPages={totalPages}
        total={data.total}
        onChange={(p) => load(p)}
      />

      {/* Create/Edit Dialog */}
      <Dialog open={drawer} onOpenChange={(open) => { if (!open) { setDrawer(false); setEditing(null); form.reset() } }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing?.id ? '编辑缺陷' : '新建缺陷'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={form.handleSubmit(doSave)} className="flex flex-col gap-4">
            <div data-invalid={!!form.formState.errors.title} aria-invalid={!!form.formState.errors.title}>
              <label className="text-sm font-medium mb-1 block">缺陷标题</label>
              <Input placeholder="缺陷标题" {...form.register('title')} />
              {form.formState.errors.title && (
                <p className="text-xs text-destructive mt-0.5">{form.formState.errors.title.message}</p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">详细描述</label>
              <Textarea rows={3} placeholder="缺陷描述" {...form.register('description')} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">严重程度</label>
                <Select value={form.watch('severity')} onValueChange={(v) => form.setValue('severity', v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(SEVERITY_MAP).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                {editing?.id ? (
                  <>
                    <label className="text-sm font-medium mb-1 block">状态</label>
                    <Select value={form.watch('status') ?? ''} onValueChange={(v) => form.setValue('status', v || undefined)}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择状态" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(STATUS_MAP).map(([k, v]) => (
                          <SelectItem key={k} value={k}>{v.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </>
                ) : null}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">处理人</label>
                <Select
                  value={form.watch('assignee_id')?.toString() ?? '__none__'}
                  onValueChange={(v) => form.setValue('assignee_id', v === '__none__' ? null : Number(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择处理人" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">未指定</SelectItem>
                    {users.map((u: any) => (
                      <SelectItem key={u.id} value={String(u.id)}>{u.nickname || u.username}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">关联用例</label>
                <Select
                  value={form.watch('case_id')?.toString() ?? '__none__'}
                  onValueChange={(v) => form.setValue('case_id', v === '__none__' ? null : Number(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="关联用例" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">未关联</SelectItem>
                    {cases.map((c: any) => (
                      <SelectItem key={c.id} value={String(c.id)}>[{c.case_id}] {c.title}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">外部ID</label>
                <Input placeholder="禅道/Jira 编号" {...form.register('external_id')} />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">外部链接</label>
                <Input placeholder="https://..." {...form.register('external_url')} />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setDrawer(false); setEditing(null); form.reset() }}>
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
            <SheetTitle>缺陷详情</SheetTitle>
          </SheetHeader>
          {detail && (
            <div className="flex flex-col gap-4 mt-4 overflow-y-auto flex-1">
              <dl className="grid grid-cols-2 border rounded-lg">
                {[
                  ['编号', detail.defect_id],
                  ['标题', detail.title],
                  ['严重程度', <Badge key="sev" variant="outline" className={severityBadgeClass(SEVERITY_MAP[detail.severity]?.color)}>{SEVERITY_MAP[detail.severity]?.label}</Badge>],
                  ['状态', <Badge key="st" variant="outline" className={statusBadgeClass(STATUS_MAP[detail.status]?.color)}>{STATUS_MAP[detail.status]?.label}</Badge>],
                  ['处理人', detail.assignee_name || '-'],
                  ['创建人', detail.creator_name || '-'],
                  ['关联用例', detail.case_title || (detail.case_id ? `#${detail.case_id}` : '-')],
                  ['外部ID', detail.external_id || '-'],
                  ['创建时间', detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '-'],
                  ['解决时间', detail.resolved_at ? new Date(detail.resolved_at).toLocaleString('zh-CN') : '-'],
                ].map(([label, value]) => (
                  <div key={label as string} className="flex flex-col border-b border-r p-2 even:border-r-0 [&:nth-last-child(-n+2)]:border-b-0">
                    <dt className="text-xs text-muted-foreground">{label}</dt>
                    <dd className="text-sm mt-0.5">{value}</dd>
                  </div>
                ))}
              </dl>

              {detail.external_url && (
                <p className="flex items-center gap-1">
                  <Link2 className="size-4" />
                  <a href={detail.external_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                    查看外部链接
                  </a>
                </p>
              )}

              {detail.description && (
                <Card size="sm">
                  <div className="text-sm font-medium px-[var(--card-spacing)] pt-[var(--card-spacing)]">详细描述</div>
                  <CardContent>
                    <pre className="whitespace-pre-wrap m-0 text-sm">{detail.description}</pre>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
