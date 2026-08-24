import { useCallback, useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router'
import { toast } from 'sonner'

import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/ui'
import { Textarea } from '@/components/ui/textarea'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  ArrowLeft, CheckCircle2, XCircle, Edit, Import, ListFilter, Loader2,
  FileText, Layers, Search,
} from '@/lib/icons'
import { fetchReviewState, reviewCase, reviewImportCases, generateTestCasesAsync, runAsyncAiTask } from '@/api/requirement'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const PRIORITY_CLASSES: Record<string, string> = {
  P0: 'border-status-danger-border bg-status-danger-muted text-status-danger',
  P1: 'border-status-warning-border bg-status-warning-muted text-status-warning',
  P2: 'border-status-info-border bg-status-info-muted text-status-info',
  P3: 'border-border bg-muted text-muted-foreground',
}

const REVIEW_STATUS_MAP: Record<string, { tone: 'success' | 'warning' | 'danger' | 'info' | 'neutral'; label: string }> = {
  pending: { tone: 'neutral', label: '待审核' },
  approved: { tone: 'success', label: '已通过' },
  rejected: { tone: 'danger', label: '已驳回' },
  edited: { tone: 'info', label: '已编辑' },
}

const REVIEW_PAGE_SIZE = 50

interface CaseItem {
  index: number
  title: string
  priority: string
  module: string
  domain: string
  preconditions: string
  steps: string
  expected_result: string
  case_type: string
  review_status: string
  edited_data: any
  imported: boolean
}

export default function ReviewPage() {
  useDocumentTitle('审查队列')
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const docId = Number(id)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<{ docTitle: string; funcCases: CaseItem[]; apiCases: CaseItem[]; summary: any } | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [activeCase, setActiveCase] = useState<CaseItem | null>(null)
  const [filter, setFilter] = useState<'all' | 'P0' | 'pending' | 'api'>('all')
  const [search, setSearch] = useState('')
  const [importing, setImporting] = useState(false)
  const [reviewing, setReviewing] = useState<number | null>(null)
  const [tab, setTab] = useState<'func' | 'api'>('func')
  const [generating, setGenerating] = useState(false)
  const [editDraft, setEditDraft] = useState<Partial<CaseItem> | null>(null)
  const [page, setPage] = useState(1)

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!Number.isInteger(docId) || docId <= 0) {
      setError('无效的需求文档 ID')
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetchReviewState(docId, signal)
      if (signal?.aborted) return
      const funcCases = (res.functional_cases || []).map((c: any) => ({
        ...c,
        ...(c.edited_data || {}),
        edited_data: c.edited_data,
        case_type: 'func',
      }))
      const apiCases = (res.api_cases || []).map((c: any) => ({
        ...c,
        ...(c.edited_data || {}),
        edited_data: c.edited_data,
        case_type: 'api',
      }))
      setData({
        docTitle: res.document_title,
        funcCases,
        apiCases,
        summary: res.summary,
      })
      setActiveCase((current) => current
        ? [...funcCases, ...apiCases].find((item) => item.index === current.index) || null
        : null)
    } catch (loadError) {
      if (!signal?.aborted) {
        setError(loadError instanceof Error ? loadError.message : '加载审查数据失败')
      }
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [docId])

  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal)
    return () => controller.abort()
  }, [load])

  const cases = useMemo(
    () => tab === 'func' ? (data?.funcCases || []) : (data?.apiCases || []),
    [data?.apiCases, data?.funcCases, tab],
  )

  const filteredCases = useMemo(() => {
    let result = cases
    if (filter === 'P0') result = result.filter((c) => c.priority === 'P0')
    if (filter === 'pending') result = result.filter((c) => c.review_status === 'pending')
    if (filter === 'api') result = result.filter((c) => c.case_type === 'api')
    if (search) {
      const s = search.toLowerCase()
      result = result.filter((c) => c.title.toLowerCase().includes(s) || (c.module || '').toLowerCase().includes(s))
    }
    return result
  }, [cases, filter, search])

  const pageCount = Math.max(1, Math.ceil(filteredCases.length / REVIEW_PAGE_SIZE))
  const pagedCases = useMemo(
    () => filteredCases.slice((page - 1) * REVIEW_PAGE_SIZE, page * REVIEW_PAGE_SIZE),
    [filteredCases, page],
  )

  useEffect(() => {
    setPage(1)
  }, [filter, search, tab])

  useEffect(() => {
    setPage((current) => Math.min(current, pageCount))
  }, [pageCount])

  const toggleSelect = (idx: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  const toggleAll = () => {
    if (selectedIds.size === filteredCases.length) setSelectedIds(new Set())
    else setSelectedIds(new Set(filteredCases.map((c) => c.index)))
  }

  const handleReview = async (caseIndex: number, action: 'approve' | 'reject') => {
    setReviewing(caseIndex)
    try {
      await reviewCase(docId, caseIndex, action)
      toast.success(action === 'approve' ? '已批准' : '已驳回')
      await load()
    } catch {
      toast.error('操作失败')
    } finally {
      setReviewing(null)
    }
  }

  const handleImport = async () => {
    if (selectedIds.size === 0) { toast.warning('请选择至少一条用例'); return }
    setImporting(true)
    try {
      const res = await reviewImportCases(docId, Array.from(selectedIds))
      toast.success(`成功导入 ${res.imported} 条，跳过 ${res.skipped} 条`)
      setSelectedIds(new Set())
      await load()
    } catch {
      toast.error('导入失败')
    } finally {
      setImporting(false)
    }
  }

  const handleRegenerate = async () => {
    setGenerating(true)
    try {
      const task = await generateTestCasesAsync(docId, { use_extraction: true })
      await runAsyncAiTask(task.id)
      toast.success('用例已重新生成')
      await load()
    } catch {
      toast.error('重新生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleEdit = async () => {
    if (!activeCase || !editDraft) return
    setReviewing(activeCase.index)
    try {
      await reviewCase(docId, activeCase.index, 'edit', editDraft)
      toast.success('编辑内容已保存')
      setEditDraft(null)
      await load()
    } catch {
      toast.error('保存编辑失败')
    } finally {
      setReviewing(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-muted-foreground">{error || '数据不存在'}</p>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => load()}>重试</Button>
          <Button variant="secondary" onClick={() => navigate('/requirement')}>返回需求列表</Button>
        </div>
      </div>
    )
  }

  const allCases = [...data.funcCases, ...data.apiCases]
  const approvedCount = allCases.filter((c) => c.review_status === 'approved').length
  const rejectedCount = allCases.filter((c) => c.review_status === 'rejected').length
  const pendingCount = allCases.filter((c) => c.review_status === 'pending').length

  const renderSteps = (steps: string) => {
    try {
      const arr = JSON.parse(steps)
      if (!Array.isArray(arr)) return <span className="text-muted-foreground text-xs">{steps}</span>
      return (
        <ol className="m-0 pl-4 space-y-0.5">
          {arr.map((s: any, i: number) => (
            <li key={i} className="text-xs">
              <span>{s.desc || s.action || s.description || `Step ${s.step || i + 1}`}</span>
              {s.expected && <span className="text-status-success ml-1">→ {s.expected}</span>}
            </li>
          ))}
        </ol>
      )
    } catch {
      return <span className="text-xs text-muted-foreground">{steps}</span>
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <Button variant="ghost" size="sm" onClick={() => navigate('/requirement')}>
          <ArrowLeft className="size-4 mr-1" /> 返回
        </Button>
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <Layers className="size-5 text-primary" />
          {data.docTitle}
        </h1>
        <div className="flex items-center gap-2 ml-auto">
          <Badge tone="neutral">{approvedCount} 已通过</Badge>
          <Badge tone="danger">{rejectedCount} 已驳回</Badge>
          <Badge tone="neutral">{pendingCount} 待审核</Badge>
          <Button size="sm" variant="secondary" onClick={handleRegenerate} disabled={generating}>
            {generating ? <Loader2 className="size-3 animate-spin" /> : null}
            重新生成
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-4">
        {/* Left: Case list */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <TabsMini value={tab} onChange={(v: 'func' | 'api') => setTab(v)} funcCount={data.funcCases.length} apiCount={data.apiCases.length} />
            </div>
            <div className="flex items-center gap-2 mt-2">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3 text-muted-foreground" />
                <Input
                  className="pl-7 h-7 text-xs"
                  placeholder="搜索…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <Select value={filter} onValueChange={(v: any) => setFilter(v)}>
                <SelectTrigger className="h-7 w-[90px] text-xs">
                  <ListFilter className="size-3 mr-1" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="P0">仅 P0</SelectItem>
                  <SelectItem value="pending">待审核</SelectItem>
                  <SelectItem value="api">仅 API</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="px-3 pb-1">
              <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                <Checkbox checked={selectedIds.size === filteredCases.length && filteredCases.length > 0} onCheckedChange={toggleAll} />
                全选 ({filteredCases.length})
              </label>
            </div>
            {filteredCases.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">暂无匹配用例</p>
            ) : (
              <div className="max-h-[52vh] divide-y overflow-y-auto">
                {pagedCases.map((c) => {
                  const isActive = activeCase?.index === c.index
                  const rv = REVIEW_STATUS_MAP[c.review_status] || REVIEW_STATUS_MAP.pending
                  return (
                    <div
                      key={c.index}
                      className={`flex w-full items-start gap-2 px-3 py-2.5 transition-colors hover:bg-muted/50 ${isActive ? 'bg-muted' : ''}`}
                    >
                      <Checkbox
                        checked={selectedIds.has(c.index)}
                        onCheckedChange={() => toggleSelect(c.index)}
                        aria-label={`选择用例：${c.title}`}
                      />
                      <button
                        type="button"
                        className="min-w-0 flex-1 rounded-sm text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        onClick={() => {
                          setActiveCase(c)
                          setEditDraft(null)
                        }}
                        aria-pressed={isActive}
                        aria-label={`查看用例：${c.title}`}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-sm font-medium truncate">{c.title}</span>
                            <Badge tone="neutral" className={PRIORITY_CLASSES[c.priority] || ''}>{c.priority}</Badge>
                            {c.case_type === 'api' && <Badge tone="neutral" className="text-xs">API</Badge>}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs text-muted-foreground">{c.module || '-'}</span>
                            <Badge tone={rv.tone} className="text-xs px-1.5 leading-[16px]">{rv.label}</Badge>
                            {c.imported && <Badge tone="neutral" className="text-xs border-status-success-border bg-status-success-muted text-status-success">已导入</Badge>}
                          </div>
                        </div>
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
            {filteredCases.length > REVIEW_PAGE_SIZE && (
              <div className="flex items-center justify-between border-t px-3 py-2">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={page === 1}
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  aria-label="上一页"
                >
                  上一页
                </Button>
                <span className="text-xs tabular-nums text-muted-foreground">第 {page} / {pageCount} 页</span>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={page === pageCount}
                  onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
                  aria-label="下一页"
                >
                  下一页
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right: Case detail */}
        <Card>
          <CardContent className="pt-4 min-h-[300px]">
            {!activeCase ? (
              <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                <FileText className="size-10 mb-2 opacity-30" />
                <p className="text-sm">选择左侧用例查看详情</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={reviewing === activeCase.index}
                      onClick={() => setEditDraft({
                        title: activeCase.title,
                        priority: activeCase.priority,
                        module: activeCase.module,
                        domain: activeCase.domain,
                        preconditions: activeCase.preconditions,
                        steps: activeCase.steps,
                        expected_result: activeCase.expected_result,
                      })}
                    >
                      <Edit className="size-3" />
                      编辑
                    </Button>
                    <h3 className="font-semibold">{activeCase.title}</h3>
                    <Badge tone="neutral" className={PRIORITY_CLASSES[activeCase.priority] || ''}>{activeCase.priority}</Badge>
                    <Badge tone="neutral">{activeCase.domain || activeCase.module || '-'}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="primary"
                      disabled={reviewing === activeCase.index || activeCase.review_status === 'approved'}
                      onClick={() => handleReview(activeCase.index, 'approve')}
                    >
                      {reviewing === activeCase.index ? <Loader2 className="size-3 animate-spin" /> : <CheckCircle2 className="size-3" />}
                      通过
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      disabled={reviewing === activeCase.index || activeCase.review_status === 'rejected'}
                      onClick={() => handleReview(activeCase.index, 'reject')}
                    >
                      <XCircle className="size-3" /> 驳回
                    </Button>
                  </div>
                </div>

                {editDraft && (
                  <Card className="border-status-warning-border bg-status-warning-muted">
                    <CardContent className="grid grid-cols-1 gap-3 pt-4 sm:grid-cols-2">
                      <div className="space-y-1 sm:col-span-2">
                        <label className="text-xs font-medium" htmlFor="review-case-title">用例标题</label>
                        <Input
                          id="review-case-title"
                          value={String(editDraft.title || '')}
                          onChange={(event) => setEditDraft((draft) => ({
                            ...draft,
                            title: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs font-medium" htmlFor="review-case-module">模块</label>
                        <Input
                          id="review-case-module"
                          value={String(editDraft.module || '')}
                          onChange={(event) => setEditDraft((draft) => ({
                            ...draft,
                            module: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs font-medium" htmlFor="review-case-priority">优先级</label>
                        <Input
                          id="review-case-priority"
                          value={String(editDraft.priority || '')}
                          onChange={(event) => setEditDraft((draft) => ({
                            ...draft,
                            priority: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="space-y-1 sm:col-span-2">
                        <label className="text-xs font-medium" htmlFor="review-case-preconditions">前置条件</label>
                        <Textarea
                          id="review-case-preconditions"
                          value={String(editDraft.preconditions || '')}
                          onChange={(event) => setEditDraft((draft) => ({
                            ...draft,
                            preconditions: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="space-y-1 sm:col-span-2">
                        <label className="text-xs font-medium" htmlFor="review-case-steps">测试步骤</label>
                        <Textarea
                          id="review-case-steps"
                          className="font-mono text-xs"
                          value={String(editDraft.steps || '')}
                          onChange={(event) => setEditDraft((draft) => ({
                            ...draft,
                            steps: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="space-y-1 sm:col-span-2">
                        <label className="text-xs font-medium" htmlFor="review-case-expected">预期结果</label>
                        <Textarea
                          id="review-case-expected"
                          value={String(editDraft.expected_result || '')}
                          onChange={(event) => setEditDraft((draft) => ({
                            ...draft,
                            expected_result: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flex flex-wrap gap-2 sm:col-span-2">
                        <Button
                          size="sm"
                          onClick={handleEdit}
                          disabled={reviewing === activeCase.index || !String(editDraft.title || '').trim()}
                        >
                          {reviewing === activeCase.index && <Loader2 className="size-3 animate-spin" />}
                          保存编辑
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setEditDraft(null)}
                          disabled={reviewing === activeCase.index}
                        >
                          取消
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {activeCase.preconditions && (
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-1">前置条件</h4>
                    <p className="text-sm">{activeCase.preconditions}</p>
                  </div>
                )}

                <div>
                  <h4 className="text-xs font-medium text-muted-foreground mb-1">测试步骤</h4>
                  {renderSteps(activeCase.steps)}
                </div>

                {activeCase.expected_result && (
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-1">预期结果</h4>
                    <p className="text-sm">{activeCase.expected_result}</p>
                  </div>
                )}

                {activeCase.edited_data && Object.keys(activeCase.edited_data).length > 0 && (
                  <Card className="border-status-warning-border bg-status-warning-muted">
                    <CardContent className="pt-3 text-xs">
                      <span className="font-medium text-status-warning">已编辑版本:</span>
                      <pre className="mt-1 whitespace-pre-wrap text-xs">{JSON.stringify(activeCase.edited_data, null, 2)}</pre>
                    </CardContent>
                  </Card>
                )}

                {activeCase.review_status !== 'pending' && (
                  <Badge tone={REVIEW_STATUS_MAP[activeCase.review_status]?.tone || 'neutral'}>
                    {REVIEW_STATUS_MAP[activeCase.review_status]?.label}
                  </Badge>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bottom bar */}
      <div className="sticky bottom-0 flex flex-col gap-2 border-t bg-background pt-3 pb-1 sm:flex-row sm:items-center sm:justify-between">
        <span className="text-sm text-muted-foreground">
          已选 {selectedIds.size} 条 · 全部 {allCases.length} 条
          {data.summary.approved > 0 && <span className="text-status-success ml-2">· {data.summary.approved} 已批准</span>}
        </span>
        <Button onClick={handleImport} disabled={importing || selectedIds.size === 0}>
          {importing ? <Loader2 className="size-4 animate-spin" /> : <Import className="size-4" />}
          导入选中用例 ({selectedIds.size})
        </Button>
      </div>
    </div>
  )
}

// ── Mini tabs for func/api switch ──

function TabsMini({ value, onChange, funcCount, apiCount }: { value: string; onChange: (v: 'func' | 'api') => void; funcCount: number; apiCount: number }) {
  return (
    <div className="flex rounded-md border bg-muted p-0.5">
      <button
        className={`px-3 py-1 text-xs rounded-sm ${value === 'func' ? 'bg-background shadow-sm font-medium' : 'text-muted-foreground'}`}
        onClick={() => onChange('func')}
      >
        功能 ({funcCount})
      </button>
      <button
        className={`px-3 py-1 text-xs rounded-sm ${value === 'api' ? 'bg-background shadow-sm font-medium' : 'text-muted-foreground'}`}
        onClick={() => onChange('api')}
      >
        API ({apiCount})
      </button>
    </div>
  )
}
