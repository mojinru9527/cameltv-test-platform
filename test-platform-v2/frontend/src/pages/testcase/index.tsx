import { PageShell } from '@/ui'
import { useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import DomainTree from '@/components/DomainTree'

import { cn } from '@/lib/utils'
import { deleteTestCase, fetchDomains, fetchTaxonomy, fetchTestCases, fetchTestCaseStats, batchUpdateCases, batchDeleteCases, fetchVersions, reviewCase, importExcel, importXmind, downloadExport } from '@/api/testcase'
import type { TaxonomyModuleNode } from '@/api/testcase'
import { countCasesByType, sortCasesNewestFirst } from './caseListFormatters'
import { buildCaseListParams, countDirectCases, flattenTaxonomyModules } from './caseTaxonomyFilters'
import { groupDomains } from '@/utils/domainNaming'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { useAuthStore } from '@/stores/auth'
import CaseDrawer from './CaseDrawer'
import MindmapPanel from './mindmap'
import VersionDialog from './VersionDialog'
import CaseFilterBar from './components/CaseFilterBar'
import CaseBatchToolbar from './components/CaseBatchToolbar'
import CaseTable from './components/CaseTable'
import CasePagination from './components/CasePagination'
import BatchDeleteDialog from './components/BatchDeleteDialog'
import ReviewDialog from './components/ReviewDialog'
import type { TestCaseVersion } from '@/types'

export default function TestCasePage() {
  useDocumentTitle('用例库')
  const hasPerm = useAuthStore((state) => state.hasPerm)
  const canCreate = hasPerm('testcase:create')
  const canUpdate = hasPerm('testcase:update')
  const canDelete = hasPerm('testcase:delete')
  const canSubmitReview = hasPerm('review:submit')
  const canApproveReview = hasPerm('review:approve')
  const projects = useAuthStore((state) => state.projects)
  const currentProjectId = useAuthStore((state) => state.currentProjectId)
  const currentProjectName = projects.find((project) => project.id === currentProjectId)?.name
    || (currentProjectId ? `项目 #${currentProjectId}` : '未选择项目')
  const canBatchSelect = canUpdate || canDelete
  // filter state (default to manual - api cases managed in apitest module)
  const [actTab, setActTab] = useState('manual')
  // 视图切换（P2a）：用例列表 / 脑图视图，?tab=mindmap 可直达（旧 /mindmap 路由重定向至此）
  const [searchParams, setSearchParams] = useSearchParams()
  const viewTab = searchParams.get('tab') === 'mindmap' ? 'mindmap' : 'list'
  const setViewTab = (next: 'list' | 'mindmap') => {
    setSearchParams(next === 'mindmap' ? { tab: 'mindmap' } : {}, { replace: true })
  }
  const [selSurface, setSelSurface] = useState('')
  const [selDomain, setSelDomain] = useState('')
  const [selModule, setSelModule] = useState('')
  const [selDirect, setSelDirect] = useState(false)
  const [caseNature, setCaseNature] = useState('')
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
  const [batchDeleteDialog, setBatchDeleteDialog] = useState(false)
  const batchDeleteInFlight = useRef(false)
  const importInputRef = useRef<HTMLInputElement>(null)
  const [importing, setImporting] = useState(false)

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
      const params = buildCaseListParams({
        surface: selSurface,
        domain: selDomain,
        modulePath: selModule,
        nature: caseNature,
        directOnly: selDirect,
      }, { page, page_size: pageSize, ...(actTab ? { case_type: actTab } : {}) })
      if (priority) params.priority = priority
      if (keyword) params.keyword = keyword
      return fetchTestCases(params, signal) as unknown as Promise<{ total: number; items: any[]; page: number; page_size: number }>
    },
    [actTab, selSurface, selDomain, selModule, selDirect, caseNature, priority, keyword, page, pageSize]
  )

  // ── Domains (secondary data, loaded independently) ──
  const { data: domainData, refetch: refetchDomains } = useApi(
    (signal) => fetchDomains(signal),
    [],
  )
  const domains = useMemo(() => domainData || [], [domainData])
  const { data: caseStats, refetch: refetchCaseStats } = useApi(
    (signal) => fetchTestCaseStats(signal),
    [],
  )
  const { data: taxonomyData, refetch: refetchTaxonomy } = useApi(
    (signal) => fetchTaxonomy({ case_type: actTab || 'all' }, signal),
    [actTab],
  )
  const taxonomy = useMemo(() => taxonomyData || [], [taxonomyData])
  const caseTypeCounts = useMemo(() => countCasesByType(caseStats), [caseStats])

  const items = useMemo(() => data?.items || [], [data?.items])
  // Sort newest first (created_at descending, fallback to id descending)
  const sortedItems = useMemo(() => sortCasesNewestFirst(items), [items])

  async function handleImportFile(file: File | undefined) {
    if (!file) return
    setImporting(true)
    try {
      const isXmind = file.name.toLowerCase().endsWith('.xmind')
      const res: any = isXmind ? await importXmind(file) : await importExcel(file)
      toast.success(`导入完成：${res?.imported ?? 0}/${res?.total ?? 0} 条`)
      setPage(1)
      refetch()
      refetchDomains()
      refetchCaseStats()
      refetchTaxonomy()
    } catch (e: any) {
      toast.error(e?.message || '导入失败')
    } finally {
      setImporting(false)
      if (importInputRef.current) importInputRef.current.value = ''
    }
  }

  async function handleExport(format: 'excel' | 'xmind') {
    try {
      const blob = await downloadExport(format, {
        ...(selSurface ? { surface: selSurface } : {}),
        ...(selDomain ? { taxonomy_domain: selDomain } : {}),
        ...(selModule ? { taxonomy_module: selModule } : {}),
        ...(selDirect ? { taxonomy_direct: 'true' } : {}),
        ...(caseNature ? { positive_negative: caseNature } : {}),
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `test-cases.${format === 'excel' ? 'xlsx' : 'xmind'}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('导出成功')
    } catch (e: any) {
      toast.error(e?.message || '导出失败')
    }
  }
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
    if (batchDeleteInFlight.current || selected.size === 0) return
    batchDeleteInFlight.current = true
    setBatchDeleting(true)
    try {
      await batchDeleteCases(Array.from(selected))
      toast.success(`已删除 ${selected.size} 条用例`)
      setSelected(new Set())
      setBatchDeleteDialog(false)
      refetch()
      refetchDomains()
      refetchCaseStats()
      refetchTaxonomy()
    } catch {
      toast.error('批量删除失败')
    } finally {
      batchDeleteInFlight.current = false
      setBatchDeleting(false)
    }
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

  const selectedSurface = useMemo(
    () => taxonomy.find((surface) => surface.surface === selSurface),
    [selSurface, taxonomy],
  )
  const taxonomyDomains = useMemo(() => selectedSurface?.domains || [], [selectedSurface])
  const selectedTaxonomyDomain = taxonomyDomains.find((domain) => domain.domain === selDomain)

  // Batch 182（FIX-173-P3-04）：域筛选下拉按 DOMAIN_GROUP_ORDER（用户端/运营后台/接口测试/其他）
  // 分组，组内按用例数降序（数量更有区分度），标签统一走 domainNaming（裸域补前缀展示）。
  const groupedTaxonomyDomains = useMemo(() => {
    return groupDomains(taxonomyDomains, (d) => d.domain).map(([group, items]) => ({
      group,
      items: [...items].sort(
        (a, b) => (b.count - a.count) || a.domain.localeCompare(b.domain, 'zh-CN'),
      ),
    }))
  }, [taxonomyDomains])

  // ── Domain tree data ──
  const domainTree = useMemo(() => {
    // 直属用例只读核算项：父级计数包含"直接归属本级、未下钻子节点"的用例，
    // 但树只渲染有子模块路径的节点。这里用父级总数减去直接子级之和推导差值，
    // 作为不可点击的统计说明行，不新增请求、不伪造 taxonomy_module 分类。
    const directCaseNode = (surface: string, domain: string, path: string, count: number): any => ({
      key: JSON.stringify({ kind: 'direct', surface, domain, path }),
      title: <span className="text-xs">直属用例 <span className="text-muted-foreground">({count})</span></span>,
      isLeaf: true,
      isAccounting: true,
      ariaLabel: `直属用例 ${count} 条，点击查看并编辑`,
    })

    const moduleNode = (surface: string, domain: string, node: TaxonomyModuleNode): any => {
      const children = node.children.map((child) => moduleNode(surface, domain, child))
      const direct = countDirectCases(node.count, node.children.map((child) => child.count))
      return {
        title: <span className="text-xs">{node.name} <span className="text-muted-foreground">({node.count})</span></span>,
        key: JSON.stringify({ kind: 'module', surface, domain, path: node.path }),
        isLeaf: node.children.length === 0,
        children: [
          ...(node.children.length > 0 && direct > 0 ? [directCaseNode(surface, domain, node.path, direct)] : []),
          ...children,
        ],
      }
    }

    return taxonomy.map((surface) => {
      const domains = surface.domains.map((domain) => {
        const modules = domain.modules.map((node) => moduleNode(surface.surface, domain.domain, node))
        const direct = countDirectCases(domain.count, domain.modules.map((node) => node.count))
        return {
          title: <span className="text-xs font-medium">{domain.domain} <span className="text-muted-foreground">({domain.count})</span></span>,
          key: JSON.stringify({ kind: 'domain', surface: surface.surface, domain: domain.domain }),
          children: [
            ...(domain.modules.length > 0 && direct > 0 ? [directCaseNode(surface.surface, domain.domain, '', direct)] : []),
            ...modules,
          ],
        }
      })
      const direct = countDirectCases(surface.count, surface.domains.map((domain) => domain.count))
      return {
        title: <span className="text-[13px] font-medium">{surface.surface} <span className="text-muted-foreground">({surface.count})</span></span>,
        key: JSON.stringify({ kind: 'surface', surface: surface.surface }),
        children: [
          ...(surface.domains.length > 0 && direct > 0 ? [directCaseNode(surface.surface, '', '', direct)] : []),
          ...domains,
        ],
      }
    })
  }, [taxonomy])

  // derived modules list — returns all modules when no domain selected so the
  // "全部模块" Select always has enough options for Radix to open it.
  const selModules = useMemo(() => {
    return selectedTaxonomyDomain
      ? flattenTaxonomyModules(selectedTaxonomyDomain.modules)
      : []
  }, [selectedTaxonomyDomain])

  // ── Actions ──
  const doDelete = async (id: number) => {
    await deleteTestCase(id)
    toast.success('已删除')
    setDeleteTarget(null)
    refetch()
    refetchDomains()
    refetchCaseStats()
    refetchTaxonomy()
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
    refetchCaseStats()
    refetchTaxonomy()
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

  const clearFilters = () => {
    setSelSurface(''); setSelDomain(''); setSelModule(''); setCaseNature(''); setPriority(''); setKeywordInput(''); setKeyword(''); setPage(1)
  }

  return (
    <PageShell
      title="用例服务"
      description="管理测试用例资产，按领域组织，支持批量操作与版本历史。"
      glass
    >
      <div className="space-y-4">
      {/* 视图切换（P2a）：用例列表 / 脑图视图 */}
      <div className="flex items-center gap-2" role="tablist" aria-label="用例视图切换">
        {([['list', '用例列表'], ['mindmap', '脑图视图']] as const).map(([k, label]) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={viewTab === k}
            className={cn(
              'rounded-md px-4 py-1 text-sm font-medium transition-colors',
              viewTab === k
                ? 'bg-accent text-accent-foreground font-semibold'
                : 'text-muted-foreground hover:text-foreground'
            )}
            onClick={() => setViewTab(k)}
          >
            {label}
          </button>
        ))}
      </div>

      {viewTab === 'mindmap' ? <MindmapPanel /> : (
      <>
      {/* Top Tabs */}
      <div className="flex items-center gap-2">
        {([
          ['manual', `功能用例 (${caseTypeCounts.manual})`],
          ['api', `接口用例 (${caseTypeCounts.api})`],
          ['ui', `UI 自动化 (${caseTypeCounts.ui})`],
          ['', `全部 (${caseTypeCounts.all})`],
        ]).map(([k, label]) => (
          <button
            key={k as string}
            type="button"
            aria-pressed={actTab === k}
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
                if (!keys.length) { setSelSurface(''); setSelDomain(''); setSelModule(''); setSelDirect(false); setPage(1); return }
                const selection = JSON.parse(keys[0]) as {
                  kind: 'surface' | 'domain' | 'module' | 'direct'
                  surface?: string
                  domain?: string
                  path?: string
                }
                setSelSurface(selection.surface || '')
                setSelDomain(selection.domain || '')
                setSelModule(selection.kind === 'module' || selection.kind === 'direct' ? selection.path || '' : '')
                setSelDirect(selection.kind === 'direct')
                setPage(1)
              }}
            />
          </CardContent>
        </Card>

        {/* Right: Filter + Table */}
        <div className="flex min-h-[540px] min-w-0 flex-1 flex-col lg:h-[calc(100vh-215px)]">
          {/* Filters */}
          <CaseFilterBar
            taxonomy={taxonomy}
            groupedTaxonomyDomains={groupedTaxonomyDomains}
            selModules={selModules}
            selSurface={selSurface}
            setSelSurface={setSelSurface}
            selDomain={selDomain}
            setSelDomain={setSelDomain}
            selModule={selModule}
            setSelModule={setSelModule}
            setSelDirect={setSelDirect}
            caseNature={caseNature}
            setCaseNature={setCaseNature}
            priority={priority}
            setPriority={setPriority}
            keywordInput={keywordInput}
            setKeywordInput={setKeywordInput}
            keyword={keyword}
            setKeyword={setKeyword}
            setPage={setPage}
            refetch={refetch}
            canCreate={canCreate}
            importing={importing}
            importInputRef={importInputRef}
            onImportFile={handleImportFile}
            onExport={handleExport}
            onNewCase={() => openEdit()}
          />

          {/* Batch toolbar */}
          {selected.size > 0 && (
            <CaseBatchToolbar
              selectedCount={selected.size}
              canUpdate={canUpdate}
              canDelete={canDelete}
              batchPriority={batchPriority}
              setBatchPriority={setBatchPriority}
              batchUpdating={batchUpdating}
              batchDeleting={batchDeleting}
              onBatchUpdate={doBatchUpdate}
              onOpenBatchDeleteDialog={() => setBatchDeleteDialog(true)}
              onCancelSelection={() => setSelected(new Set())}
            />
          )}

          {/* Table + Pagination — flex-1 scrollable */}
          <div className="flex-1 min-h-0 flex flex-col">
            <CaseTable
              isLoading={isLoading}
              isError={isError}
              error={error}
              data={data}
              sortedItems={sortedItems}
              refetch={refetch}
              activeFilters={{ keyword, selSurface, selDomain, selModule, caseNature, priority }}
              onClearFilters={clearFilters}
              canCreate={canCreate}
              canBatchSelect={canBatchSelect}
              selected={selected}
              onToggleSelectAll={toggleSelectAll}
              onToggleSelect={toggleSelect}
              canSubmitReview={canSubmitReview}
              canApproveReview={canApproveReview}
              canUpdate={canUpdate}
              canDelete={canDelete}
              deleteTarget={deleteTarget}
              setDeleteTarget={setDeleteTarget}
              onDelete={doDelete}
              onEdit={openEdit}
              onOpenVersionHistory={openVersionHistory}
              onOpenReviewDialog={openReviewDialog}
            />

            {/* Pagination */}
            <CasePagination
              page={data?.page || 1}
              totalPages={totalPages}
              total={data?.total || 0}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
            />
          </div>
        </div>
      </div>
      </>
      )}

      <CaseDrawer
        open={drawer}
        editing={editing}
        domains={domains}
        onClose={() => { setDrawer(false); setEditing(null) }}
        onSaved={onSaved}
      />

      <VersionDialog
        open={versionDialog}
        onClose={() => setVersionDialog(false)}
        caseData={versionCase}
        versions={versions}
      />

      <BatchDeleteDialog
        open={batchDeleteDialog}
        onOpenChange={setBatchDeleteDialog}
        count={selected.size}
        projectName={currentProjectName}
        deleting={batchDeleting}
        onConfirm={doBatchDelete}
      />

      {/* ── Review Dialog (batch-34) ── */}
      <ReviewDialog
        open={reviewDialog}
        onOpenChange={setReviewDialog}
        action={reviewAction}
        comment={reviewComment}
        setComment={setReviewComment}
        reviewing={reviewing}
        onReview={doReview}
      />
    </div>
    </PageShell>
  )
}
