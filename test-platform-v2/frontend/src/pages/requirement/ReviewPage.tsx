import { useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
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
import { fetchReviewState, reviewCase, reviewImportCases, generateTestCases } from '@/api/requirement'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const PRIORITY_CLASSES: Record<string, string> = {
  P0: 'border-red-200 bg-red-50 text-red-700',
  P1: 'border-orange-200 bg-orange-50 text-orange-700',
  P2: 'border-blue-200 bg-blue-50 text-blue-700',
  P3: 'border-gray-200 bg-gray-50 text-gray-500',
}

const REVIEW_STATUS_MAP: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
  pending: { variant: 'secondary', label: '待审核' },
  approved: { variant: 'default', label: '已通过' },
  rejected: { variant: 'destructive', label: '已驳回' },
  edited: { variant: 'outline', label: '已编辑' },
}

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

  const load = () => {
    setLoading(true)
    setError(null)
    fetchReviewState(docId)
      .then((res) => {
        setData({
          docTitle: res.document_title,
          funcCases: (res.functional_cases || []).map((c: any) => ({ ...c, case_type: 'func' })),
          apiCases: (res.api_cases || []).map((c: any) => ({ ...c, case_type: 'api' })),
          summary: res.summary,
        })
      })
      .catch(() => setError('加载审查数据失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [docId])

  const cases = tab === 'func' ? (data?.funcCases || []) : (data?.apiCases || [])

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
      load()
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
      load()
    } catch {
      toast.error('导入失败')
    } finally {
      setImporting(false)
    }
  }

  const handleRegenerate = async () => {
    setGenerating(true)
    try {
      await generateTestCases(docId)
      toast.success('用例已重新生成')
      load()
    } catch {
      toast.error('重新生成失败')
    } finally {
      setGenerating(false)
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
        <Button variant="outline" onClick={() => navigate('/requirement')}>返回需求列表</Button>
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
              {s.expected && <span className="text-green-600 ml-1">→ {s.expected}</span>}
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
          <Badge variant="default">{approvedCount} 已通过</Badge>
          <Badge variant="destructive">{rejectedCount} 已驳回</Badge>
          <Badge variant="secondary">{pendingCount} 待审核</Badge>
          <Button size="sm" variant="outline" onClick={handleRegenerate} disabled={generating}>
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
                  placeholder="搜索..."
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
          <CardContent className="p-0 max-h-[60vh] overflow-y-auto">
            <div className="px-3 pb-1">
              <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                <Checkbox checked={selectedIds.size === filteredCases.length && filteredCases.length > 0} onCheckedChange={toggleAll} />
                全选 ({filteredCases.length})
              </label>
            </div>
            {filteredCases.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">暂无匹配用例</p>
            ) : (
              <div className="divide-y">
                {filteredCases.map((c) => {
                  const isActive = activeCase?.index === c.index
                  const rv = REVIEW_STATUS_MAP[c.review_status] || REVIEW_STATUS_MAP.pending
                  return (
                    <button
                      key={c.index}
                      className={`w-full text-left px-3 py-2.5 hover:bg-muted/50 transition-colors ${isActive ? 'bg-muted' : ''}`}
                      onClick={() => setActiveCase(c)}
                    >
                      <div className="flex items-start gap-2">
                        <Checkbox
                          checked={selectedIds.has(c.index)}
                          onCheckedChange={() => toggleSelect(c.index)}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-sm font-medium truncate">{c.title}</span>
                            <Badge variant="outline" className={PRIORITY_CLASSES[c.priority] || ''}>{c.priority}</Badge>
                            {c.case_type === 'api' && <Badge variant="outline" className="text-[10px]">API</Badge>}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[11px] text-muted-foreground">{c.module || '-'}</span>
                            <Badge variant={rv.variant} className="text-[10px] px-1.5 leading-[16px]">{rv.label}</Badge>
                            {c.imported && <Badge variant="outline" className="text-[10px] border-green-200 bg-green-50 text-green-700">已导入</Badge>}
                          </div>
                        </div>
                      </div>
                    </button>
                  )
                })}
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
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{activeCase.title}</h3>
                    <Badge variant="outline" className={PRIORITY_CLASSES[activeCase.priority] || ''}>{activeCase.priority}</Badge>
                    <Badge variant="outline">{activeCase.domain || activeCase.module || '-'}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="default"
                      disabled={reviewing === activeCase.index || activeCase.review_status === 'approved'}
                      onClick={() => handleReview(activeCase.index, 'approve')}
                    >
                      {reviewing === activeCase.index ? <Loader2 className="size-3 animate-spin" /> : <CheckCircle2 className="size-3" />}
                      通过
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={reviewing === activeCase.index || activeCase.review_status === 'rejected'}
                      onClick={() => handleReview(activeCase.index, 'reject')}
                    >
                      <XCircle className="size-3" /> 驳回
                    </Button>
                  </div>
                </div>

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
                  <Card className="border-amber-200 bg-amber-50/50">
                    <CardContent className="pt-3 text-xs">
                      <span className="font-medium text-amber-700">已编辑版本:</span>
                      <pre className="mt-1 whitespace-pre-wrap text-[11px]">{JSON.stringify(activeCase.edited_data, null, 2)}</pre>
                    </CardContent>
                  </Card>
                )}

                {activeCase.review_status !== 'pending' && (
                  <Badge variant={REVIEW_STATUS_MAP[activeCase.review_status]?.variant || 'secondary'}>
                    {REVIEW_STATUS_MAP[activeCase.review_status]?.label}
                  </Badge>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bottom bar */}
      <div className="flex items-center justify-between sticky bottom-0 bg-background border-t pt-3 pb-1">
        <span className="text-sm text-muted-foreground">
          已选 {selectedIds.size} 条 · 全部 {allCases.length} 条
          {data.summary.approved > 0 && <span className="text-green-600 ml-2">· {data.summary.approved} 已批准</span>}
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
