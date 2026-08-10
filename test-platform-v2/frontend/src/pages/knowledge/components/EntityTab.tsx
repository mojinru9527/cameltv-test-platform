import { useEffect, useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/ui'
import { Badge } from '@/ui'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/ui'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { toast } from 'sonner'
import {
  fetchEntities,
  fetchEntityStats,
  fetchEntityDetail,
  fetchRelations,
  approveRelation,
  rejectRelation,
} from '@/api/knowledge'
import type { KnowledgeEntityBrief, KnowledgeEntity, KnowledgeEntityStats, KnowledgeRelation } from '@/types'
import { Search, CheckCircle2, XCircle, Loader2 } from '@/lib/icons'

const ENTITY_TYPES = [
  { v: '_all', l: '全部类型' },
  { v: 'module', l: '模块' },
  { v: 'api', l: 'API' },
  { v: 'field', l: '字段' },
  { v: 'requirement', l: '需求' },
  { v: 'test_case', l: '用例' },
  { v: 'defect', l: '缺陷' },
]
const TYPE_LABEL: Record<string, string> = Object.fromEntries(ENTITY_TYPES.map((t) => [t.v, t.l]))
const TYPE_COLORS: Record<string, string> = {
  module: 'bg-status-accent-muted text-status-accent',
  api: 'bg-status-info-muted text-status-info',
  field: 'bg-status-success-muted text-status-success',
  requirement: 'bg-status-accent-muted text-status-accent',
  test_case: 'bg-status-warning-muted text-status-warning',
  defect: 'bg-status-danger-muted text-status-danger',
}
const REL_LABELS: Record<string, string> = {
  contains: '包含',
  executed_by: '执行来源',
  depends_on: '依赖',
  affects: '影响',
  covers: '覆盖',
  generated_from: '生成自',
}
const REVIEW_LABELS: Record<string, string> = {
  pending: '待审核',
  approved: '已采纳',
  rejected: '已驳回',
}

export default function EntityTab() {
  const [rows, setRows] = useState<KnowledgeEntityBrief[]>([])
  const [stats, setStats] = useState<KnowledgeEntityStats>({ total: 0, by_type: {}, missing_source: 0, test_case_total: 0 })
  const [loading, setLoading] = useState(true)
  const [entityType, setEntityType] = useState('_all')
  const [domain, setDomain] = useState('_all')
  const [keyword, setKeyword] = useState('')

  // Detail sheet
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<KnowledgeEntity | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [relations, setRelations] = useState<KnowledgeRelation[]>([])
  const [relationsLoading, setRelationsLoading] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    const params = {
      entity_type: entityType === '_all' ? undefined : entityType,
      keyword: keyword || undefined,
      knowledge_domain: domain === '_all' ? undefined : domain,
    }
    Promise.all([
      fetchEntities({ ...params, limit: 200 }, controller.signal),
      fetchEntityStats(params, controller.signal),
    ])
      .then(([nextRows, nextStats]) => {
        if (controller.signal.aborted) return
        setRows(nextRows)
        setStats(nextStats)
      })
      .catch(() => {
        if (!controller.signal.aborted) toast.error('加载实体列表失败')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [entityType, keyword, domain])

  // Load detail + relations when a row is clicked
  useEffect(() => {
    if (selectedId === null) {
      setDetail(null)
      setRelations([])
      return
    }
    const controller = new AbortController()
    setDetailLoading(true)
    setRelationsLoading(true)
    fetchEntityDetail(selectedId, controller.signal)
      .then((value) => { if (!controller.signal.aborted) setDetail(value) })
      .catch(() => { if (!controller.signal.aborted) toast.error('加载实体详情失败') })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false) })
    fetchRelations({ entity_id: selectedId, limit: 100 }, controller.signal)
      .then((value) => { if (!controller.signal.aborted) setRelations(value) })
      .catch(() => { if (!controller.signal.aborted) toast.error('加载关系列表失败') })
      .finally(() => { if (!controller.signal.aborted) setRelationsLoading(false) })
    return () => controller.abort()
  }, [selectedId])

  const handleApprove = async (relId: number) => {
    try {
      const updated = await approveRelation(relId)
      setRelations((prev) => prev.map((r) => (r.id === relId ? updated : r)))
      toast.success('关系已采纳')
    } catch {
      toast.error('采纳失败')
    }
  }

  const handleReject = async (relId: number) => {
    try {
      const updated = await rejectRelation(relId)
      setRelations((prev) => prev.map((r) => (r.id === relId ? updated : r)))
      toast.success('关系已驳回')
    } catch {
      toast.error('驳回失败')
    }
  }

  return (
    <div className="space-y-4">
      {/* Stats cards */}
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
        {['api', 'field', 'requirement', 'test_case', 'defect'].map((t) => (
          <Card key={t} className="p-3">
            <div className="text-xs text-muted-foreground">{TYPE_LABEL[t]}</div>
            <div className="text-2xl font-bold">
              {t === 'test_case' && (stats.test_case_total ?? 0) > 0
                ? `${stats.by_type.test_case ?? 0}/${stats.test_case_total}`
                : (stats.by_type[t] ?? 0)}
            </div>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Select value={entityType} onValueChange={(v) => setEntityType(v)}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ENTITY_TYPES.map((t) => (
              <SelectItem key={t.v} value={t.v}>{t.l}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={domain} onValueChange={(v) => setDomain(v)}>
          <SelectTrigger className="w-28" aria-label="按知识域筛选">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="_all">全部域</SelectItem>
            <SelectItem value="project">项目知识</SelectItem>
            <SelectItem value="platform">平台研发</SelectItem>
          </SelectContent>
        </Select>
        <div className="relative flex-1 max-w-sm">
          <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索实体名称/描述…"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            className="pl-9"
          />
        </div>
        <span className="text-sm text-muted-foreground">
          {domain === '_all' ? '项目全量/筛选结果' : (domain === 'platform' ? '平台研发' : '项目知识')} {stats.total} 个 · 当前展示 {rows.length} 个
        </span>
      </div>

      {stats.missing_source > 0 && (
        <div role="status" className="rounded-md border border-status-warning-border bg-status-warning-muted px-3 py-2 text-sm text-status-warning">
          {stats.missing_source} 个实体缺少可追溯来源；当前仅做标记，不会伪造来源信息。
        </div>
      )}

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">类型</TableHead>
                <TableHead>名称</TableHead>
                <TableHead className="w-56 hidden lg:table-cell">来源</TableHead>
                <TableHead className="w-32 hidden md:table-cell">置信度</TableHead>
                <TableHead className="w-24 hidden sm:table-cell">审核</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-5 w-14" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-48" /></TableCell>
                    <TableCell className="hidden md:table-cell"><Skeleton className="h-5 w-16" /></TableCell>
                    <TableCell className="hidden sm:table-cell"><Skeleton className="h-5 w-12" /></TableCell>
                  </TableRow>
                ))
              ) : rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    暂无实体数据。请先在「图谱」Tab 中执行实体提取。
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((r) => (
                  <TableRow
                    key={r.id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => setSelectedId(r.id)}
                  >
                    <TableCell>
                      <Badge className={TYPE_COLORS[r.entity_type] ?? 'bg-muted text-muted-foreground'}>
                        {TYPE_LABEL[r.entity_type] ?? r.entity_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium text-sm">{r.name}</div>
                      <div className="text-xs text-muted-foreground truncate max-w-64" title={r.description}>{r.description}</div>
                    </TableCell>
                    <TableCell className="hidden lg:table-cell">
                      {r.source_title ? (
                        <div className="flex flex-col gap-0.5 min-w-0">
                          <span className="text-xs text-muted-foreground truncate max-w-48" title={r.source_title}>{r.source_title}</span>
                          {r.source_type && <Badge tone="neutral" className="text-xs w-fit">{r.source_type}</Badge>}
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">来源待补</span>
                      )}
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      <div className="flex items-center gap-2">
                        <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className="size-full origin-left rounded-full transition-transform duration-200"
                            style={{
                              transform: `scaleX(${Math.min(1, Math.max(0, r.confidence))})`,
                              backgroundColor: r.confidence >= 0.8
                                ? 'var(--color-status-success-solid)'
                                : r.confidence >= 0.6
                                  ? 'var(--color-status-warning-solid)'
                                  : 'var(--color-status-danger-solid)',
                            }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground">{Math.round(r.confidence * 100)}%</span>
                      </div>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">
                      <span className="text-xs text-muted-foreground">—</span>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Detail Sheet */}
      <Sheet open={selectedId !== null} onOpenChange={(open) => { if (!open) setSelectedId(null) }}>
        <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>实体详情</SheetTitle>
          </SheetHeader>
          {detailLoading ? (
            <div className="space-y-3 mt-6">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : detail ? (
            <div className="mt-6 space-y-4">
              <div className="flex items-center gap-2">
                <Badge className={TYPE_COLORS[detail.entity_type] ?? ''}>
                  {TYPE_LABEL[detail.entity_type] ?? detail.entity_type}
                </Badge>
                <span className="text-lg font-semibold">{detail.name}</span>
              </div>
              <p className="text-sm text-muted-foreground">{detail.description}</p>
              {detail.source_title && (
                <div className="rounded-md border p-3 text-sm space-y-1">
                  <div className="font-medium text-xs text-muted-foreground">来源溯源</div>
                  <div className="flex items-center gap-2">
                    {detail.source_type && <Badge tone="neutral" className="text-xs">{detail.source_type}</Badge>}
                    <span className="text-sm">{detail.source_title}</span>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">实体键: </span>
                  <code className="text-xs bg-muted px-1 rounded">{detail.entity_key}</code>
                </div>
                <div>
                  <span className="text-muted-foreground">置信度: </span>
                  {(detail.confidence * 100).toFixed(0)}%
                </div>
                <div>
                  <span className="text-muted-foreground">审核状态: </span>
                  {REVIEW_LABELS[detail.review_status] ?? detail.review_status}
                </div>
                {detail.business_ref_id && (
                  <div>
                    <span className="text-muted-foreground">业务 ID: </span>
                    {detail.business_ref_type} #{detail.business_ref_id}
                  </div>
                )}
              </div>

              {/* Relations section */}
              <div className="pt-4 border-t">
                <h4 className="text-sm font-medium mb-3">
                  关联关系 ({relations.length})
                </h4>
                {relationsLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-12 w-full" />
                    <Skeleton className="h-12 w-full" />
                  </div>
                ) : relations.length === 0 ? (
                  <p className="text-sm text-muted-foreground">暂无关联关系</p>
                ) : (
                  <div className="space-y-2">
                    {relations.map((rel) => (
                      <div
                        key={rel.id}
                        className="flex items-center gap-3 p-3 rounded-lg border bg-muted/30"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <Badge tone="neutral" className="text-xs">
                              {REL_LABELS[rel.relation_type] ?? rel.relation_type}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              → 实体 #{rel.to_entity_id}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                            <span>置信度: {(rel.confidence * 100).toFixed(0)}%</span>
                            <span>|</span>
                            <Badge
                              tone="neutral"
                              className={
                                rel.review_status === 'approved'
                                  ? 'bg-status-success-muted text-status-success'
                                  : rel.review_status === 'rejected'
                                  ? 'bg-status-danger-muted text-status-danger'
                                  : 'bg-muted text-muted-foreground'
                              }
                            >
                              {REVIEW_LABELS[rel.review_status] ?? rel.review_status}
                            </Badge>
                          </div>
                        </div>
                        {rel.review_status === 'pending' && (
                          <div className="flex items-center gap-1 shrink-0">
                            <Button
                              size="icon"
                              variant="ghost"
                              className="size-8 text-status-success hover:text-status-success"
                              onClick={(e) => { e.stopPropagation(); handleApprove(rel.id) }}
                              aria-label={`通过关系 ${rel.relation_type || rel.id}`}
                            >
                              <CheckCircle2 className="size-4" />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="size-8 text-status-danger hover:text-status-danger"
                              onClick={(e) => { e.stopPropagation(); handleReject(rel.id) }}
                              aria-label={`驳回关系 ${rel.relation_type || rel.id}`}
                            >
                              <XCircle className="size-4" />
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground mt-6">实体不存在或已被删除</p>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
