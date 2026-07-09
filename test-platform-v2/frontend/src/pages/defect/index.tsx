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
  Trash2,
  Loader2,
  ArrowRight,
  Download,
  History,
  MessageSquare,
  Paperclip,
  Send,
  File,
  ArrowLeftRight,
  RefreshCw,
} from '@/lib/icons'
import { useRef, useState } from 'react'
import {
  createDefect,
  deleteDefect,
  fetchDefectStats,
  fetchDefects,
  updateDefect,
  fetchTransitions,
  transitionDefect,
  fetchComments,
  addComment,
  fetchAttachments,
  uploadAttachment,
  getAttachmentUrl,
  deleteAttachment,
} from '@/api/defect'
import { fetchTestCases } from '@/api/testcase'
import { fetchUsers } from '@/api/system'
import { pushDefect, pullDefect } from '@/api/integration'
import { useAuthStore } from '@/stores/auth'
import type { DefectItem, DefectTransition, DefectComment, DefectAttachment } from '@/types'
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
import SearchInput from '@/components/SearchInput'
import { AsyncState } from '@/components/state'
import useApi from '@/hooks/useApi'
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
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const SEVERITY_MAP: Record<string, { color: string; label: string }> = {
  P0: { color: 'red', label: 'P0-致命' },
  P1: { color: 'orange', label: 'P1-严重' },
  P2: { color: 'gold', label: 'P2-一般' },
  P3: { color: 'blue', label: 'P3-建议' },
}

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  open: { color: 'red', label: '待处理' },
  acknowledged: { color: 'orange', label: '已确认' },
  fixing: { color: 'processing', label: '修复中' },
  reviewing: { color: 'purple', label: '待审核' },
  verified: { color: 'green', label: '已验证' },
  closed: { color: 'default', label: '已关闭' },
  reopened: { color: 'red', label: '已重开' },
  // legacy compatibility (backend normalizes these)
  confirmed: { color: 'orange', label: '已确认' },
  pending_review: { color: 'purple', label: '待回归' },
  rejected: { color: 'default', label: '已拒绝' },
  in_progress: { color: 'processing', label: '处理中' },
  resolved: { color: 'green', label: '已解决' },
  wontfix: { color: 'default', label: '不修复' },
}

const STATUS_TRANSITIONS: Record<string, string[]> = {
  'open': ['acknowledged', 'closed'],
  'acknowledged': ['fixing', 'closed'],
  'fixing': ['reviewing', 'closed'],
  'reviewing': ['verified', 'reopened'],
  'verified': ['closed', 'reopened'],
  'closed': ['reopened'],
  'reopened': ['acknowledged', 'closed'],
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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

  // filters
  const [fSeverity, setFSeverity] = useState<string | undefined>()
  const [fStatus, setFStatus] = useState<string | undefined>()
  const [fKeyword, setFKeyword] = useState('')
  const [page, setPage] = useState(1)

  // main data
  const { data, isLoading, isError, error, refetch } = useApi<any>(
    () => {
      const params: any = { page, page_size: 20 }
      if (fSeverity) params.severity = fSeverity
      if (fStatus) params.status = fStatus
      if (fKeyword) params.keyword = fKeyword
      return fetchDefects(params)
    },
    [fSeverity, fStatus, fKeyword, page],
  )

  // stats (non-critical, silent errors)
  const { data: statsData, refetch: refetchStats } = useApi<any>(
    () => fetchDefectStats(),
    { showErrorToast: false },
  )
  const stats = statsData || { total: 0, by_severity: {} as Record<string, number>, by_status: {} as Record<string, number> }

  // sheet / detail
  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<DefectItem | null>(null)
  const [detail, setDetail] = useState<DefectItem | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  // delete confirm
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  // ── Transitions ──
  const [transitionOpen, setTransitionOpen] = useState(false)
  const [transitionTarget, setTransitionTarget] = useState<string>('')
  const [transitionComment, setTransitionComment] = useState('')
  const [transitionLoading, setTransitionLoading] = useState(false)

  const { data: transitions, refetch: refetchTransitions } = useApi<DefectTransition[]>(
    () => {
      if (!detail?.id) return Promise.resolve([])
      return fetchTransitions(detail.id)
    },
    [detail?.id],
  )

  // ── Comments ──
  const [commentText, setCommentText] = useState('')
  const [commentSubmitting, setCommentSubmitting] = useState(false)

  const { data: comments, refetch: refetchComments } = useApi<DefectComment[]>(
    () => {
      if (!detail?.id) return Promise.resolve([])
      return fetchComments(detail.id)
    },
    [detail?.id],
  )

  // ── Attachments ──
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const { data: attachments, refetch: refetchAttachments } = useApi<DefectAttachment[]>(
    () => {
      if (!detail?.id) return Promise.resolve([])
      return fetchAttachments(detail.id)
    },
    [detail?.id],
  )

  const form = useForm<DefectFormValues>({
    resolver: zodResolver(defectFormSchema),
    defaultValues: { title: '', description: '', severity: 'P2', status: undefined, assignee_id: null, case_id: null, external_id: '', external_url: '' },
  })

  // select options
  const [users, setUsers] = useState<any[]>([])
  const [cases, setCases] = useState<any[]>([])

  const openCreate = () => {
    setEditing(null)
    form.reset({ title: '', description: '', severity: 'P2', status: undefined, assignee_id: null, case_id: null, external_id: '', external_url: '' })
    setDrawer(true)
    fetchUsers().then((r: any) => setUsers(r || [])).catch(() => setUsers([]))
    fetchTestCases({ page_size: 200 }).then((r: any) => setCases(r?.items || [])).catch(() => setCases([]))
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
    fetchUsers().then((u: any) => setUsers(u || [])).catch(() => setUsers([]))
    fetchTestCases({ page_size: 200 }).then((c: any) => setCases(c?.items || [])).catch(() => setCases([]))
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
      refetch()
      refetchStats()
    } finally {
      setSaving(false)
    }
  }

  const doDelete = async () => {
    if (deleteTarget == null) return
    await deleteDefect(deleteTarget)
    toast.success('已删除')
    setDeleteTarget(null)
    refetch()
    refetchStats()
  }

  const openDetail = (r: DefectItem) => { setDetail(r); setDetailOpen(true) }

  // ── Transition handlers ──
  const openTransition = (toStatus: string) => {
    setTransitionTarget(toStatus)
    setTransitionComment('')
    setTransitionOpen(true)
  }

  const handleTransitionConfirm = async () => {
    if (!detail?.id || !transitionTarget) return
    setTransitionLoading(true)
    try {
      const updated = await transitionDefect(detail.id, {
        to_status: transitionTarget,
        comment: transitionComment || undefined,
      })
      toast.success(`状态已更新为 ${STATUS_MAP[transitionTarget]?.label || transitionTarget}`)
      setDetail(updated)
      setTransitionOpen(false)
      refetchTransitions()
      refetch()
      refetchStats()
    } catch {
      // error toast handled by interceptor
    } finally {
      setTransitionLoading(false)
    }
  }

  // ── Comment handlers ──
  const handleAddComment = async () => {
    if (!detail?.id || !commentText.trim()) return
    setCommentSubmitting(true)
    try {
      await addComment(detail.id, commentText.trim())
      setCommentText('')
      toast.success('评论已添加')
      refetchComments()
    } catch {
      // error toast handled by interceptor
    } finally {
      setCommentSubmitting(false)
    }
  }

  // ── Attachment handlers ──
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !detail?.id) return
    setUploading(true)
    try {
      await uploadAttachment(detail.id, file)
      toast.success('文件已上传')
      refetchAttachments()
    } catch {
      // error toast handled by interceptor
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDeleteAttachment = async (attachmentId: number) => {
    if (!detail?.id) return
    try {
      await deleteAttachment(detail.id, attachmentId)
      toast.success('附件已删除')
      refetchAttachments()
    } catch {
      // error toast handled by interceptor
    }
  }

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
        <Select value={fSeverity ?? '__all__'} onValueChange={(v) => { setFSeverity(v === '__all__' ? undefined : v); setPage(1) }}>
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

        <Select value={fStatus ?? '__all__'} onValueChange={(v) => { setFStatus(v === '__all__' ? undefined : v); setPage(1) }}>
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
          onChange={(v) => { setFKeyword(v); setPage(1) }}
          onSearch={refetch}
          placeholder="搜索缺陷标题"
          inputClassName="w-[220px]"
          clearable
        />

        <Button variant="outline" size="default" onClick={refetch}>
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

      {/* Table with AsyncState */}
      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={data}
        onRetry={refetch}
        loadingVariant="skeleton"
        skeletonType="table"
        loadingRows={5}
        emptyTitle="暂无缺陷"
        emptyDescription="当前筛选条件下没有缺陷记录"
      >
        {(d) => (
          <>
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
                  {d.items.map((r: any) => (
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

        {/* Pagination */}
        <Pagination
          page={d.page}
          totalPages={Math.max(1, Math.ceil(d.total / d.page_size))}
          total={d.total}
          onChange={(p) => setPage(p)}
        />
      </>
        )}
      </AsyncState>

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
            <Tabs defaultValue="info" className="flex flex-col flex-1 mt-4 overflow-hidden">
              <TabsList className="w-full">
                <TabsTrigger value="info" className="flex-1">详情</TabsTrigger>
                <TabsTrigger value="comments" className="flex-1">评论</TabsTrigger>
                <TabsTrigger value="attachments" className="flex-1">附件</TabsTrigger>
                <TabsTrigger value="history" className="flex-1">历史</TabsTrigger>
              </TabsList>

              {/* ── Tab 1: 详情 ── */}
              <TabsContent value="info" className="flex-1 overflow-y-auto mt-4">
                {/* Status badge + transition buttons */}
                <div className="flex items-center gap-2 mb-4 flex-wrap">
                  <span className="text-sm text-muted-foreground">状态:</span>
                  <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[detail.status]?.color)}>
                    {STATUS_MAP[detail.status]?.label || detail.status}
                  </Badge>
                  {STATUS_TRANSITIONS[detail.status]?.length > 0 && (
                    <div className="flex items-center gap-1.5 ml-2">
                      <ArrowLeftRight className="size-3.5 text-muted-foreground" />
                      {STATUS_TRANSITIONS[detail.status].map((toStatus) => (
                        <Button
                          key={toStatus}
                          size="xs"
                          variant="outline"
                          onClick={() => openTransition(toStatus)}
                        >
                          <ArrowRight className="size-3 mr-1" />
                          {STATUS_MAP[toStatus]?.label || toStatus}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>

                <dl className="grid grid-cols-2 border rounded-lg">
                  {[
                    ['编号', detail.defect_id],
                    ['标题', detail.title],
                    ['严重程度', <Badge key="sev" variant="outline" className={severityBadgeClass(SEVERITY_MAP[detail.severity]?.color)}>{SEVERITY_MAP[detail.severity]?.label}</Badge>],
                    ['处理人', detail.assignee_name || '-'],
                    ['创建人', detail.creator_name || '-'],
                    ['关联用例', detail.case_title || (detail.case_id ? `#${detail.case_id}` : '-')],
                    ['外部ID', detail.external_id || '-'],
                    ['创建时间', detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '-'],
                    ['更新时间', detail.updated_at ? new Date(detail.updated_at).toLocaleString('zh-CN') : '-'],
                    ['解决时间', detail.resolved_at ? new Date(detail.resolved_at).toLocaleString('zh-CN') : '-'],
                  ].map(([label, value]) => (
                    <div key={label as string} className="flex flex-col border-b border-r p-2 even:border-r-0 [&:nth-last-child(-n+2)]:border-b-0">
                      <dt className="text-xs text-muted-foreground">{label}</dt>
                      <dd className="text-sm mt-0.5">{value}</dd>
                    </div>
                  ))}
                </dl>

                {detail.external_url && (
                  <p className="flex items-center gap-1 mt-4">
                    <Link2 className="size-4" />
                    <a href={detail.external_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                      查看外部链接
                    </a>
                  </p>
                )}

                {/* V2.6: Sync buttons */}
                {hasPerm('integration:sync') && (
                  <div className="flex items-center gap-2 mt-4 pt-3 border-t">
                    <span className="text-xs text-muted-foreground">同步:</span>
                    <Button
                      variant="outline" size="sm"
                      onClick={async () => {
                        const iid = prompt('请输入集成配置 ID (可在集成配置页查看):')
                        if (!iid) return
                        try {
                          await pushDefect(detail.id, Number(iid))
                          toast.success('推送成功')
                          if (refetch) refetch()
                        } catch (e: any) { toast.error(e?.message || '推送失败') }
                      }}
                    >
                      <RefreshCw className="size-3 mr-1" />推送
                    </Button>
                    {detail.external_id && (
                      <Button
                        variant="outline" size="sm"
                        onClick={async () => {
                          const iid = prompt('请输入集成配置 ID:')
                          if (!iid) return
                          try {
                            await pullDefect(detail.id, Number(iid))
                            toast.success('拉取成功')
                            if (refetch) refetch()
                          } catch (e: any) { toast.error(e?.message || '拉取失败') }
                        }}
                      >
                        <RefreshCw className="size-3 mr-1" />拉取
                      </Button>
                    )}
                  </div>
                )}

                {detail.description && (
                  <Card size="sm" className="mt-4">
                    <div className="text-sm font-medium px-[var(--card-spacing)] pt-[var(--card-spacing)]">详细描述</div>
                    <CardContent>
                      <pre className="whitespace-pre-wrap m-0 text-sm">{detail.description}</pre>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              {/* ── Tab 2: 评论 ── */}
              <TabsContent value="comments" className="flex flex-col flex-1 overflow-hidden mt-4">
                <div className="flex-1 overflow-y-auto space-y-3">
                  {comments && comments.length > 0 ? (
                    comments.map((c) => (
                      <div key={c.id} className="border rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-medium">{c.author_name || '匿名'}</span>
                          <span className="text-xs text-muted-foreground">
                            {c.created_at ? new Date(c.created_at).toLocaleString('zh-CN') : '-'}
                          </span>
                        </div>
                        <p className="text-sm whitespace-pre-wrap">{c.content}</p>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-muted-foreground text-sm py-8">暂无评论</div>
                  )}
                </div>
                <Separator className="my-3" />
                <div className="flex gap-2">
                  <Textarea
                    rows={2}
                    placeholder="输入评论..."
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        e.preventDefault()
                        handleAddComment()
                      }
                    }}
                    className="flex-1"
                  />
                  <Button
                    size="sm"
                    onClick={handleAddComment}
                    disabled={commentSubmitting || !commentText.trim()}
                    className="self-end"
                  >
                    {commentSubmitting ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                  </Button>
                </div>
              </TabsContent>

              {/* ── Tab 3: 附件 ── */}
              <TabsContent value="attachments" className="flex flex-col flex-1 overflow-hidden mt-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm text-muted-foreground">
                    {attachments ? `${attachments.length} 个文件` : '加载中...'}
                  </span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={handleFileSelect}
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                  >
                    {uploading ? (
                      <Loader2 className="size-4 animate-spin mr-1" />
                    ) : (
                      <Plus className="size-4 mr-1" />
                    )}
                    上传文件
                  </Button>
                </div>
                <div className="flex-1 overflow-y-auto space-y-2">
                  {attachments && attachments.length > 0 ? (
                    attachments.map((att) => (
                      <div key={att.id} className="flex items-center gap-3 border rounded-lg p-3">
                        <File className="size-5 text-muted-foreground shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{att.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatFileSize(att.file_size)}
                            {att.uploader_name ? ` · ${att.uploader_name}` : ''}
                            {att.created_at ? ` · ${new Date(att.created_at).toLocaleString('zh-CN')}` : ''}
                          </p>
                        </div>
                        <a
                          href={getAttachmentUrl(detail.id, att.id)}
                          download={att.filename}
                          className="shrink-0"
                        >
                          <Button size="xs" variant="ghost" type="button">
                            <Download className="size-4" />
                          </Button>
                        </a>
                        <Button
                          size="xs"
                          variant="ghost"
                          className="text-destructive hover:text-destructive shrink-0"
                          onClick={() => handleDeleteAttachment(att.id)}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-muted-foreground text-sm py-8">暂无附件</div>
                  )}
                </div>
              </TabsContent>

              {/* ── Tab 4: 历史 ── */}
              <TabsContent value="history" className="flex-1 overflow-y-auto mt-4">
                {transitions && transitions.length > 0 ? (
                  <div className="relative pl-6 border-l-2 border-muted space-y-4">
                    {transitions.map((t) => (
                      <div key={t.id} className="relative">
                        <div className="absolute -left-[25px] top-1 size-2.5 rounded-full border-2 border-muted-foreground/30 bg-background" />
                        <div className="flex items-center gap-1.5 text-sm">
                          <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[t.from_status]?.color)}>
                            {STATUS_MAP[t.from_status]?.label || t.from_status}
                          </Badge>
                          <ArrowRight className="size-3 text-muted-foreground" />
                          <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[t.to_status]?.color)}>
                            {STATUS_MAP[t.to_status]?.label || t.to_status}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
                          {t.operator_name && <span>{t.operator_name}</span>}
                          <span>{t.created_at ? new Date(t.created_at).toLocaleString('zh-CN') : '-'}</span>
                        </div>
                        {t.comment && (
                          <p className="text-sm text-muted-foreground mt-1 bg-muted/50 rounded px-2 py-1">{t.comment}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground text-sm py-8">暂无流转记录</div>
                )}
              </TabsContent>
            </Tabs>
          )}
        </SheetContent>
      </Sheet>

      {/* Transition Dialog */}
      <Dialog open={transitionOpen} onOpenChange={setTransitionOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>状态流转</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">当前状态:</span>
              <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[detail?.status ?? '']?.color)}>
                {STATUS_MAP[detail?.status ?? '']?.label || detail?.status || '-'}
              </Badge>
              <ArrowRight className="size-4 text-muted-foreground" />
              <Badge variant="outline" className={statusBadgeClass(STATUS_MAP[transitionTarget]?.color)}>
                {STATUS_MAP[transitionTarget]?.label || transitionTarget}
              </Badge>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">备注（可选）</label>
              <Textarea
                rows={3}
                placeholder="输入流转备注..."
                value={transitionComment}
                onChange={(e) => setTransitionComment(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTransitionOpen(false)}>取消</Button>
            <Button onClick={handleTransitionConfirm} disabled={transitionLoading}>
              {transitionLoading && <Loader2 className="size-4 animate-spin mr-1" />}
              确认流转
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
