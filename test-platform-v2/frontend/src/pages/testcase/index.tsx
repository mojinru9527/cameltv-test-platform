import { Badge, Button, PageShell } from '@/ui'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
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
import { Textarea } from '@/components/ui/textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group'
import DomainTree from '@/components/DomainTree'
import Pagination from '@/components/Pagination'
import { AsyncState } from '@/components/state'

import { Search, RotateCcw, Plus, Edit, Trash2, History, FileCheck, CheckCircle2, XCircle, Send } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { deleteTestCase, fetchDomains, fetchTestCases, batchUpdateCases, batchDeleteCases, fetchVersions, reviewCase } from '@/api/testcase'
import { formatNumberedText, formatStepActions, formatStepExpectations, sortCasesNewestFirst } from './caseListFormatters'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import CaseDrawer from './CaseDrawer'
import VersionDialog from './VersionDialog'
import type { TestCaseVersion } from '@/types'

import type { BadgeTone } from '@/ui'
const PRIORITY_TONES: Record<string, BadgeTone> = { P0: 'danger', P1: 'warning', P2: 'info', P3: 'neutral' }
const REVIEW_LABELS: Record<string, string> = { draft: '草稿', submitted: '已提交', approved: '已通过', rejected: '已驳回' }
const REVIEW_TONES: Record<string, BadgeTone> = { draft: 'neutral', submitted: 'info', approved: 'success', rejected: 'danger' }

export default function TestCasePage() {
  useDocumentTitle('用例库')
  // filter state (default to manual - api cases managed in apitest module)
  const [actTab, setActTab] = useState('manual')
  const [selDomain, setSelDomain] = useState('')
  const [selModule, setSelModule] = useState('')
  const [priority, setPriority] = useState('')
  const [keywordInput, setKeywordInput] = useState('')
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // drawer
  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<any>(null)

  // batch selection
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [batchDeleting, setBatchDeleting] = useState(false)
  const [batchUpdating, setBatchUpdating] = useState(false)
  const [batchPriority, setBatchPriority] = useState('')

  // delete dialog
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  // import/export

  // version history
  const [versionDialog, setVersionDialog] = useState(false)
  const [versionCase, setVersionCase] = useState<any>(null)
  const [versions, setVersions] = useState<TestCaseVersion[]>([])

  // ── Review actions (batch-34) ──
  const [reviewDialog, setReviewDialog] = useState(false)
  const [reviewTarget, setReviewTarget] = useState<any>(null)
  const [reviewAction, setReviewAction] = useState<string>('')
  const [reviewComment, setReviewComment] = useState('')
  const [reviewing, setReviewing] = useState(false)

  // ── Main data fetching with useApi ──
  const { data, isLoading, isError, error, refetch } = useApi(
    (signal) => {
      const params: any = { page, page_size: pageSize }
      if (actTab) params.case_type = actTab
      if (selDomain) params.domain = selDomain
      if (selModule) params.module = selModule
      if (priority) params.priority = priority
      if (keyword) params.keyword = keyword
      return fetchTestCases(params, signal) as unknown as Promise<{ total: number; items: any[]; page: number; page_size: number }>
    },
    [actTab, selDomain, selModule, priority, keyword, page, pageSize]
  )

  // ── Domains (secondary data, loaded independently) ──
  const { data: domainData, refetch: refetchDomains } = useApi(
    (signal) => fetchDomains(signal),
    [],
  )
  const domains = domainData || []

  const items = data?.items || []
  // Sort newest first (created_at descending, fallback to id descending)
  const sortedItems = useMemo(() => sortCasesNewestFirst(items), [items])
  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1

  // ── Selection helpers ──
  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }
  const toggleSelectAll = () => {
    if (selected.size === sortedItems.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(sortedItems.map((r: any) => r.id)))
    }
  }

  // ── Batch operations ──
  const doBatchDelete = async () => {
    setBatchDeleting(true)
    try {
      await batchDeleteCases(Array.from(selected))
      toast.success(`已删除 ${selected.size} 条用例`)
      setSelected(new Set())
      refetch()
    } catch {
      toast.error('批量删除失败')
    } finally { setBatchDeleting(false) }
  }

  const doBatchUpdate = async () => {
    if (!batchPriority) { toast.error('请选择目标优先级'); return }
    setBatchUpdating(true)
    try {
      await batchUpdateCases(Array.from(selected), { priority: batchPriority })
      toast.success(`已更新 ${selected.size} 条用例`)
      setSelected(new Set())
      setBatchPriority('')
      refetch()
    } catch {
      toast.error('批量更新失败')
    } finally { setBatchUpdating(false) }
  }

  // Filter out "接口测试" domain (api cases managed in apitest module)
  const visibleDomains = useMemo(() => domains.filter((d: any) => d.domain !== '接口测试'), [domains])

  // ── Domain tree data ──
  const domainTree = useMemo(() => {
    return visibleDomains.map((d: any) => ({
      title: <span className="text-[13px]">{d.domain} <span className="text-muted-foreground">({d.count})</span></span>,
      key: d.domain,
      children: d.modules?.map((m: any) => ({
        title: <span className="text-xs">{m.module} <span className="text-muted-foreground">({m.count})</span></span>,
        key: `${d.domain}::${m.module}`,
        isLeaf: true,
      })) || [],
    }))
  }, [domains])

  // derived modules list — returns all modules when no domain selected so the
  // "全部模块" Select always has enough options for Radix to open it.
  const selModules = useMemo(() => {
    if (selDomain) {
      const d = visibleDomains.find((x: any) => x.domain === selDomain)
      return d?.modules?.map((m: any) => ({ value: m.module, label: `${m.module} (${m.count})` })) || []
    }
    // No domain selected → merge all modules from all domains (deduped by name)
    const seen = new Set<string>()
    const all: { value: string; label: string }[] = []
    for (const d of visibleDomains) {
      for (const m of (d.modules || [])) {
        if (seen.has(m.module)) continue
        seen.add(m.module)
        all.push({ value: m.module, label: `${m.module} (${m.count})` })
      }
    }
    return all
  }, [selDomain, visibleDomains])

  // ── Actions ──
  const doDelete = async (id: number) => {
    await deleteTestCase(id)
    toast.success('已删除')
    setDeleteTarget(null)
    refetch()
  }

  const openEdit = (row?: any) => {
    setEditing(row || null)
    setDrawer(true)
  }

  const onSaved = () => {
    setDrawer(false)
    setEditing(null)
    refetch()
    refetchDomains()
  }

  // ── Version history ──

  const openVersionHistory = async (row: any) => {
    setVersionCase(row)
    setVersionDialog(true)
    try {
      const data = await fetchVersions(row.id)
      setVersions(data)
    } catch { setVersions([]) }
  }

  // ── Review handling (batch-34) ──
  const openReviewDialog = (row: any, action: string) => {
    setReviewTarget(row)
    setReviewAction(action)
    setReviewComment('')
    setReviewDialog(true)
  }

  const doReview = async () => {
    if (!reviewTarget) return
    setReviewing(true)
    try {
      await reviewCase(reviewTarget.id, reviewAction, reviewComment)
      toast.success(reviewAction === 'submit' ? '已提交评审' : reviewAction === 'approve' ? '已通过' : '已驳回')
      setReviewDialog(false)
      setReviewTarget(null)
      refetch()
    } catch {
      toast.error('评审操作失败')
    } finally {
      setReviewing(false)
    }
  }

  return (
    <PageShell
      title="用例服务"
      description="管理测试用例资产，按领域组织，支持批量操作与版本历史。"
      glass
    >
      <div className="space-y-4">
      {/* Top Tabs */}
      <div className="flex items-center gap-2">
        {([
          ['', '全部 (901)'],
          ['manual', '功能用例 (795)'],
        ]).map(([k, label]) => (
          <button
            key={k as string}
            type="button"
            className={cn(
              'rounded-md px-4 py-1 text-sm font-medium transition-colors',
              actTab === k
                ? 'bg-accent text-accent-foreground font-semibold'
                : 'text-muted-foreground hover:text-foreground'
            )}
            onClick={() => { setActTab(k as string); setPage(1) }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Body: Tree + Table */}
      <div className="flex gap-4">
        {/* Left: Domain Tree */}
        <Card size="sm" className="ui-surface hidden w-[220px] shrink-0 h-[calc(100vh-215px)] overflow-y-auto lg:block">
          <CardHeader className="border-b pb-2">
            <CardTitle className="text-[13px]">模块分类</CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <DomainTree
              treeData={domainTree}
              onSelect={(keys) => {
                if (!keys.length) { setSelDomain(''); setSelModule(''); setPage(1); return }
                const key = keys[0]
                if (key.includes('::')) {
                  const [d, m] = key.split('::')
                  setSelDomain(d); setSelModule(m); setPage(1)
                } else {
                  setSelDomain(key); setSelModule(''); setPage(1)
                }
              }}
            />
          </CardContent>
        </Card>

        {/* Right: Filter + Table */}
        <div className="flex min-h-[540px] min-w-0 flex-1 flex-col lg:h-[calc(100vh-215px)]">
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Select value={selDomain || undefined} onValueChange={(v) => { setSelDomain(v || ''); setSelModule(''); setPage(1) }}>
              <SelectTrigger className="w-full sm:w-[130px]" size="sm" aria-label="按用例域筛选">
                <SelectValue placeholder="全部域" />
              </SelectTrigger>
              <SelectContent position="popper">
                <SelectItem value="">全部域</SelectItem>
                {visibleDomains.map((d: any) => (
                  <SelectItem key={d.domain} value={d.domain}>{d.domain}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selModule || undefined} onValueChange={(v) => { setSelModule(v || ''); setPage(1) }}>
              <SelectTrigger className="w-full sm:w-[150px]" size="sm" aria-label="按用例模块筛选">
                <SelectValue placeholder="全部模块" />
              </SelectTrigger>
              <SelectContent position="popper">
                <SelectItem value="">全部模块</SelectItem>
                {selModules.map((m: any) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={priority || undefined} onValueChange={(v) => { setPriority(v || ''); setPage(1) }}>
              <SelectTrigger className="w-full sm:w-[100px]" size="sm" aria-label="按用例优先级筛选">
                <SelectValue placeholder="全部优先级" />
              </SelectTrigger>
              <SelectContent position="popper">
                <SelectItem value="">全部优先级</SelectItem>
                {['P0', 'P1', 'P2', 'P3'].map((v) => (
                  <SelectItem key={v} value={v}>{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <InputGroup className="w-full sm:w-[240px]">
              <InputGroupAddon>
                <Search className="size-3.5" />
              </InputGroupAddon>
              <InputGroupInput
                placeholder="搜索标题/关键字"
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const nextKeyword = keywordInput.trim()
                    setPage(1)
                    if (nextKeyword === keyword) refetch()
                    else setKeyword(nextKeyword)
                  }
                }}
              />
            </InputGroup>

            <Button size="sm" onClick={() => {
              const nextKeyword = keywordInput.trim()
              setPage(1)
              if (nextKeyword === keyword) refetch()
              else setKeyword(nextKeyword)
            }}>
              <Search className="size-3.5" data-icon="inline-start" />
              搜索
            </Button>
            <Button size="sm" variant="secondary" onClick={() => {
              setSelDomain(''); setSelModule(''); setPriority(''); setKeywordInput(''); setKeyword(''); setPage(1)
            }}>
              <RotateCcw className="size-3.5" data-icon="inline-start" />
              重置
            </Button>
            <div className="hidden flex-1 sm:block" />
            <Button size="sm" className="w-full sm:w-auto" onClick={() => openEdit()}>
              <Plus className="size-3.5" data-icon="inline-start" />
              新建用例
            </Button>
          </div>

          {/* Batch toolbar */}
          {selected.size > 0 && (
            <div className="flex items-center gap-2 rounded-md border bg-accent/30 px-3 py-2">
              <span className="text-sm font-medium">已选 {selected.size} 条</span>
              <Select value={batchPriority || undefined} onValueChange={setBatchPriority}>
                <SelectTrigger className="w-[100px]" size="sm" aria-label="批量设置优先级">
                  <SelectValue placeholder="优先级" />
                </SelectTrigger>
                <SelectContent position="popper">
                  {['P0','P1','P2','P3'].map(v => (
                    <SelectItem key={v} value={v}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button size="sm" variant="secondary" onClick={doBatchUpdate} disabled={batchUpdating || !batchPriority}>
                {batchUpdating ? '更新中...' : '批量更新'}
              </Button>
              <div className="flex-1" />
              <Button size="sm" variant="danger" onClick={doBatchDelete} disabled={batchDeleting}>
                <Trash2 className="size-3.5" data-icon="inline-start" />
                {batchDeleting ? '删除中...' : `批量删除 (${selected.size})`}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>取消</Button>
            </div>
          )}

          {/* Table + Pagination — flex-1 scrollable */}
          <div className="flex-1 min-h-0 flex flex-col">
            <div
              className="flex-1 min-h-0 overflow-auto rounded-md border"
              role="region"
              aria-label="测试用例数据表"
              tabIndex={0}
            >
          <AsyncState
            isLoading={isLoading}
            isError={isError}
            error={error}
            data={data?.items}
            onRetry={refetch}
            emptyTitle="暂无测试用例"
            emptyDescription="点击「新建用例」开始创建"
            skeletonType="table"
            loadingRows={4}
          >
            {() => (
            <div className="min-w-0 overflow-x-auto">
              <Table className="ui-table min-w-[900px] [&_td]:py-2.5">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[40px]">
                      <Checkbox
                        checked={selected.size === sortedItems.length && sortedItems.length > 0}
                        onCheckedChange={toggleSelectAll}
                        aria-label="选择当前页全部用例"
                      />
                    </TableHead>
                    <TableHead className="w-[100px]">模块名称</TableHead>
                    <TableHead className="w-[160px]">用例标题</TableHead>
                    <TableHead className="w-[70px]">用例等级</TableHead>
                    <TableHead className="w-[180px]">前置条件</TableHead>
                    <TableHead className="w-[200px]">操作步骤</TableHead>
                    <TableHead className="w-[200px]">预期结果</TableHead>
                    <TableHead className="w-[60px]">评审</TableHead>
                    <TableHead className="sticky right-0 z-20 w-[132px] bg-card shadow-[-10px_0_18px_-16px_hsl(var(--foreground))]">
                      操作
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedItems.map((r: any) => (
                    <TableRow key={r.id}>
                      <TableCell>
                        <Checkbox
                          checked={selected.has(r.id)}
                          onCheckedChange={() => toggleSelect(r.id)}
                          aria-label={`选择用例：${r.title || r.id}`}
                        />
                      </TableCell>
                      <TableCell className="max-w-[100px] truncate">
                        <span className="line-clamp-1">{r.module || '......'}</span>
                      </TableCell>
                      <TableCell className="max-w-[160px] truncate">
                        <span className="line-clamp-1" title={r.title}>{r.title || '......'}</span>
                      </TableCell>
                      <TableCell>
                        <Badge tone={PRIORITY_TONES[r.priority] || 'neutral'}>
                          {r.priority}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[180px] truncate text-xs">
                        <span className="line-clamp-1">{formatNumberedText(r.preconditions).join(' ') || '......'}</span>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-xs">
                        <span className="line-clamp-1">{formatStepActions(r.steps).join(' ') || '......'}</span>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-xs">
                        <span className="line-clamp-1">{formatStepExpectations(r.steps, r.expected_result).join(' ') || '......'}</span>
                      </TableCell>
                      <TableCell>
                        <Badge tone={REVIEW_TONES[r.review_status] || 'neutral'} className="text-xs">
                          {REVIEW_LABELS[r.review_status] || r.review_status || '草稿'}
                        </Badge>
                      </TableCell>
                      <TableCell className="sticky right-0 z-10 bg-card shadow-[-10px_0_18px_-16px_hsl(var(--foreground))]">
                        <div className="flex items-center gap-1">
                          <Button
                            size="icon-xs"
                            variant="ghost"
                            onClick={() => openVersionHistory(r)}
                            aria-label={`查看版本历史：${r.title || r.id}`}
                          >
                            <History className="size-3" aria-hidden="true" />
                          </Button>
                          {/* Review actions (batch-34) */}
                          {r.review_status === 'draft' && (
                            <Button
                              size="icon-xs"
                              variant="ghost"
                              onClick={() => openReviewDialog(r, 'submit')}
                              aria-label={`提交评审：${r.title || r.id}`}
                            >
                              <Send className="size-3 text-blue-600" aria-hidden="true" />
                            </Button>
                          )}
                          {r.review_status === 'submitted' && (
                            <>
                              <Button
                                size="icon-xs"
                                variant="ghost"
                                onClick={() => openReviewDialog(r, 'approve')}
                                aria-label={`通过评审：${r.title || r.id}`}
                              >
                                <CheckCircle2 className="size-3 text-green-600" aria-hidden="true" />
                              </Button>
                              <Button
                                size="icon-xs"
                                variant="ghost"
                                onClick={() => openReviewDialog(r, 'reject')}
                                aria-label={`驳回评审：${r.title || r.id}`}
                              >
                                <XCircle className="size-3 text-red-600" aria-hidden="true" />
                              </Button>
                            </>
                          )}
                          <Button
                            size="icon-xs"
                            variant="ghost"
                            onClick={() => openEdit(r)}
                            aria-label={`编辑用例：${r.title || r.id}`}
                          >
                            <Edit className="size-3" aria-hidden="true" />
                          </Button>
                          <AlertDialog open={deleteTarget === r.id} onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}>
                            <AlertDialogTrigger asChild>
                              <Button
                                size="icon-xs"
                                variant="ghost"
                                className="text-destructive hover:bg-destructive/10"
                                onClick={() => setDeleteTarget(r.id)}
                                aria-label={`删除用例：${r.title || r.id}`}
                              >
                                <Trash2 className="size-3" aria-hidden="true" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent size="sm">
                              <AlertDialogHeader>
                                <AlertDialogTitle>确定删除？</AlertDialogTitle>
                                <AlertDialogDescription>此操作不可撤销。</AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>取消</AlertDialogCancel>
                                <AlertDialogAction variant="destructive" onClick={() => doDelete(r.id)}>删除</AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            )}
          </AsyncState>
            </div>

          {/* Pagination */}
          <div className="flex shrink-0 flex-col items-stretch justify-between gap-3 border-t pt-2 sm:flex-row sm:items-center sm:gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">每页</span>
              <Select value={String(pageSize)} onValueChange={(v) => { setPageSize(Number(v)); setPage(1) }}>
                <SelectTrigger className="w-[80px]" size="sm" aria-label="每页显示条数"><SelectValue /></SelectTrigger>
                <SelectContent position="popper">
                  {[20, 50, 100].map(n => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground">条</span>
            </div>
            <Pagination
              page={data?.page || 1}
              totalPages={totalPages}
              total={data?.total || 0}
              onChange={(p) => setPage(p)}
            />
          </div>
          </div>
        </div>
      </div>

      <CaseDrawer
        open={drawer}
        editing={editing}
        domains={visibleDomains}
        onClose={() => { setDrawer(false); setEditing(null) }}
        onSaved={onSaved}
      />

      <VersionDialog
        open={versionDialog}
        onClose={() => setVersionDialog(false)}
        caseData={versionCase}
        versions={versions}
      />

      {/* ── Review Dialog (batch-34) ── */}
      <AlertDialog open={reviewDialog} onOpenChange={setReviewDialog}>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>
              {reviewAction === 'submit' ? '提交评审' : reviewAction === 'approve' ? '通过评审' : '驳回用例'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {reviewAction === 'submit'
                ? '确认将此用例提交评审？提交后状态变为"已提交"。'
                : reviewAction === 'approve'
                  ? '确认通过此用例的评审？'
                  : '请填写驳回原因：'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          {(reviewAction === 'reject') && (
            <div className="my-3">
              <Textarea
                placeholder="驳回原因..."
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                rows={3}
              />
            </div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setReviewDialog(false)}>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={doReview}
              variant={reviewAction === 'reject' ? 'destructive' : 'default'}
              disabled={reviewing || (reviewAction === 'reject' && !reviewComment.trim())}
            >
              {reviewing ? '处理中...' : reviewAction === 'submit' ? '确认提交' : reviewAction === 'approve' ? '确认通过' : '确认驳回'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
    </PageShell>
  )
}
