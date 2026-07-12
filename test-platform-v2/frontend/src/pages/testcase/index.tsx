import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
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
import PageHeader from '@/components/PageHeader'
import { AsyncState } from '@/components/state'

import { Search, RotateCcw, Plus, Edit, Trash2, Download, Upload, FileSpreadsheet, History, ClipboardCheck } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { deleteTestCase, fetchDomains, fetchTestCases, batchUpdateCases, batchDeleteCases, exportExcelUrl, exportXmindUrl, importExcel, importXmind, fetchVersions, reviewCase } from '@/api/testcase'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import CaseDrawer from './CaseDrawer'
import VersionDialog from './VersionDialog'
import type { TestCaseVersion } from '@/types'

const PRIORITY_COLORS: Record<string, string> = { P0: 'red', P1: 'orange', P2: 'blue', P3: 'default' }
const REVIEW_LABELS: Record<string, string> = { draft: '草稿', submitted: '已提交', approved: '已通过', rejected: '已驳回' }
const REVIEW_COLORS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = { draft: 'secondary', submitted: 'outline', approved: 'default', rejected: 'destructive' }

export default function TestCasePage() {
  useDocumentTitle('用例库')
  // domains are loaded independently (used for tree + filter dropdowns)
  const [domains, setDomains] = useState<any[]>([])

  // filter state
  const [actTab, setActTab] = useState('')
  const [selDomain, setSelDomain] = useState('')
  const [selModule, setSelModule] = useState('')
  const [priority, setPriority] = useState('')
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)

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
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [importFormat, setImportFormat] = useState<'xmind' | 'excel'>('excel')
  const [importing, setImporting] = useState(false)

  // version history
  const [versionDialog, setVersionDialog] = useState(false)
  const [versionCase, setVersionCase] = useState<any>(null)
  const [versions, setVersions] = useState<TestCaseVersion[]>([])

  // ── Main data fetching with useApi ──
  const { data, isLoading, isError, error, refetch } = useApi(
    () => {
      const params: any = { page, page_size: 20 }
      if (actTab) params.case_type = actTab
      if (selDomain) params.domain = selDomain
      if (selModule) params.module = selModule
      if (priority) params.priority = priority
      if (keyword) params.keyword = keyword
      return fetchTestCases(params) as unknown as Promise<{ total: number; items: any[]; page: number; page_size: number }>
    },
    [actTab, selDomain, selModule, priority, keyword, page]
  )

  // ── Domains (secondary data, loaded independently) ──
  const loadDomains = useCallback(async () => {
    try {
      const d: any = await fetchDomains()
      setDomains(d || [])
    } catch { /* handled by interceptor */ }
  }, [])

  useEffect(() => { loadDomains() }, [loadDomains])

  const items = data?.items || []
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
    if (selected.size === items.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(items.map((r: any) => r.id)))
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

  // ── Domain tree data ──
  const domainTree = useMemo(() => {
    return domains.map((d: any) => ({
      title: <span className="text-[13px]">{d.domain} <span className="text-muted-foreground">({d.count})</span></span>,
      key: d.domain,
      children: d.modules?.map((m: any) => ({
        title: <span className="text-xs">{m.module} <span className="text-muted-foreground">({m.count})</span></span>,
        key: `${d.domain}::${m.module}`,
        isLeaf: true,
      })) || [],
    }))
  }, [domains])

  // derived modules list
  const selModules = useMemo(() => {
    if (!selDomain) return []
    const d = domains.find((x: any) => x.domain === selDomain)
    return d?.modules?.map((m: any) => ({ value: m.module, label: `${m.module} (${m.count})` })) || []
  }, [selDomain, domains])

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
    loadDomains()
  }

  // ── Import/Export handlers ──

  const handleExport = (format: 'excel' | 'xmind') => {
    const params: Record<string, string> = {}
    if (selDomain) params.domain = selDomain
    if (selModule) params.module = selModule
    const url = format === 'excel' ? exportExcelUrl(params) : exportXmindUrl(params)
    const a = document.createElement('a')
    a.href = url
    a.download = format === 'excel' ? 'test-cases.xlsx' : 'test-cases.xmind'
    a.click()
  }

  const handleImportClick = (format: 'xmind' | 'excel') => {
    setImportFormat(format)
    fileInputRef.current?.click()
  }

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    try {
      const result = importFormat === 'excel' ? await importExcel(file) : await importXmind(file)
      toast.success(`导入完成：${result.imported} / ${result.total} 条用例已创建`)
      refetch()
      loadDomains()
    } catch { /* handled by interceptor */ }
    finally {
      setImporting(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
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

  return (
    <div className="space-y-4">
      <PageHeader title="用例服务" />

      {/* Top Tabs */}
      <div className="flex items-center gap-2">
        {([
          ['', '全部 (901)'],
          ['manual', '功能用例 (795)'],
          ['api', '接口用例 (106)'],
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
        <Card size="sm" className="w-[220px] shrink-0 max-h-[calc(100vh-230px)] overflow-y-auto">
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
        <div className="flex-1 min-w-0 space-y-3">
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <Select value={selDomain || undefined} onValueChange={(v) => { setSelDomain(v || ''); setSelModule(''); setPage(1) }}>
              <SelectTrigger className="w-[130px]" size="sm">
                <SelectValue placeholder="按域筛选" />
              </SelectTrigger>
              <SelectContent>
                {domains.map((d: any) => (
                  <SelectItem key={d.domain} value={d.domain}>{d.domain}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selModule || undefined} onValueChange={(v) => { setSelModule(v || ''); setPage(1) }}>
              <SelectTrigger className="w-[150px]" size="sm">
                <SelectValue placeholder="按模块筛选" />
              </SelectTrigger>
              <SelectContent>
                {selModules.map((m: any) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={priority || undefined} onValueChange={(v) => { setPriority(v || ''); setPage(1) }}>
              <SelectTrigger className="w-[100px]" size="sm">
                <SelectValue placeholder="优先级" />
              </SelectTrigger>
              <SelectContent>
                {['P0', 'P1', 'P2', 'P3'].map((v) => (
                  <SelectItem key={v} value={v}>{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <InputGroup className="w-[220px]">
              <InputGroupAddon>
                <Search className="size-3.5" />
              </InputGroupAddon>
              <InputGroupInput
                placeholder="搜索标题/编号/接口"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') refetch() }}
              />
            </InputGroup>

            <Button size="sm" onClick={() => setPage(1)}>
              <Search className="size-3.5" data-icon="inline-start" />
              搜索
            </Button>
            <Button size="sm" variant="outline" onClick={refetch}>
              <RotateCcw className="size-3.5" data-icon="inline-start" />
            </Button>
            <div className="flex-1" />
            {/* Import/Export dropdown */}
            <div className="flex items-center gap-1">
              <Button size="sm" variant="outline" onClick={() => handleExport('excel')} title="导出 Excel">
                <Download className="size-3.5" data-icon="inline-start" />
                Excel
              </Button>
              <Button size="sm" variant="outline" onClick={() => handleExport('xmind')} title="导出 Xmind">
                <Download className="size-3.5" data-icon="inline-start" />
                Xmind
              </Button>
              <Button size="sm" variant="outline" onClick={() => handleImportClick('excel')} disabled={importing} title="导入 Excel">
                <Upload className="size-3.5" data-icon="inline-start" />
                导入
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept={importFormat === 'excel' ? '.xlsx,.xls' : '.xmind'}
                className="hidden"
                onChange={handleFileSelected}
              />
            </div>
            <Button size="sm" onClick={() => openEdit()}>
              <Plus className="size-3.5" data-icon="inline-start" />
              新建用例
            </Button>
          </div>

          {/* Batch toolbar */}
          {selected.size > 0 && (
            <div className="flex items-center gap-2 rounded-md border bg-accent/30 px-3 py-2">
              <span className="text-sm font-medium">已选 {selected.size} 条</span>
              <Select value={batchPriority || undefined} onValueChange={setBatchPriority}>
                <SelectTrigger className="w-[100px]" size="sm">
                  <SelectValue placeholder="优先级" />
                </SelectTrigger>
                <SelectContent>
                  {['P0','P1','P2','P3'].map(v => (
                    <SelectItem key={v} value={v}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button size="sm" variant="outline" onClick={doBatchUpdate} disabled={batchUpdating || !batchPriority}>
                {batchUpdating ? '更新中...' : '批量更新'}
              </Button>
              <div className="flex-1" />
              <Button size="sm" variant="destructive" onClick={doBatchDelete} disabled={batchDeleting}>
                <Trash2 className="size-3.5" data-icon="inline-start" />
                {batchDeleting ? '删除中...' : `批量删除 (${selected.size})`}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>取消</Button>
            </div>
          )}

          {/* Table */}
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
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[40px]">
                      <Checkbox
                        checked={selected.size === items.length && items.length > 0}
                        onCheckedChange={toggleSelectAll}
                      />
                    </TableHead>
                    <TableHead className="w-[160px]">编号</TableHead>
                    <TableHead>标题</TableHead>
                    <TableHead className="w-[120px]">模块</TableHead>
                    <TableHead className="w-[60px]">状态</TableHead>
                    <TableHead className="w-[80px]">评审</TableHead>
                    <TableHead className="w-[140px]">API</TableHead>
                    <TableHead className="w-[120px]">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((r: any) => (
                    <TableRow key={r.id}>
                      <TableCell>
                        <Checkbox
                          checked={selected.has(r.id)}
                          onCheckedChange={() => toggleSelect(r.id)}
                        />
                      </TableCell>
                      <TableCell className="max-w-[160px] truncate">{r.case_id || '-'}</TableCell>
                      <TableCell className="max-w-0 truncate">
                        <div className="flex items-center gap-1">
                          <Badge variant={PRIORITY_COLORS[r.priority] === 'red' ? 'destructive' : PRIORITY_COLORS[r.priority] === 'orange' ? 'secondary' : 'default'}>
                            {r.priority}
                          </Badge>
                          {r.case_type === 'api' && (
                            <Badge variant="secondary" className="bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                              接口
                            </Badge>
                          )}
                          <span className="truncate">{r.title}</span>
                        </div>
                      </TableCell>
                      <TableCell className="max-w-[120px] truncate">{r.module}</TableCell>
                      <TableCell>
                        <Badge variant={
                          r.status === 'active' ? 'default'
                            : r.status === 'draft' ? 'secondary'
                            : r.status === 'archived' ? 'destructive'
                            : 'outline'
                        }>
                          {r.status === 'active' ? '启用' : r.status === 'draft' ? '草稿' : r.status === 'archived' ? '归档' : r.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={REVIEW_COLORS[r.review_status] || 'secondary'} className="text-[10px]">
                          {REVIEW_LABELS[r.review_status] || r.review_status || '草稿'}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[140px] truncate font-mono text-xs">
                        {r.api_method ? <span>{r.api_method} {r.api_endpoint}</span> : '-'}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button size="icon-xs" variant="ghost" onClick={() => openVersionHistory(r)} title="版本历史">
                            <History className="size-3" />
                          </Button>
                          <Button size="icon-xs" variant="ghost" onClick={() => openEdit(r)}>
                            <Edit className="size-3" />
                          </Button>
                          <AlertDialog open={deleteTarget === r.id} onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}>
                            <AlertDialogTrigger asChild>
                              <Button size="icon-xs" variant="ghost" className="text-destructive hover:bg-destructive/10" onClick={() => setDeleteTarget(r.id)}>
                                <Trash2 className="size-3" />
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

          {/* Pagination */}
          <Pagination
            page={data?.page || 1}
            totalPages={totalPages}
            total={data?.total || 0}
            onChange={(p) => setPage(p)}
          />
        </div>
      </div>

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
    </div>
  )
}
