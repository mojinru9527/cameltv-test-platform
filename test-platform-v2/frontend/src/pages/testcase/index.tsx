import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
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

import { Search, RotateCcw, Plus, Edit, Trash2 } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { deleteTestCase, fetchDomains, fetchTestCases, batchUpdateCases, batchDeleteCases } from '@/api/testcase'
import CaseDrawer from './CaseDrawer'

const PRIORITY_COLORS: Record<string, string> = { P0: 'red', P1: 'orange', P2: 'blue', P3: 'default' }

export default function TestCasePage() {
  // data
  const [data, setData] = useState({ total: 0, items: [] as any[], page: 1, page_size: 20 })
  const [domains, setDomains] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  // filter state
  const [actTab, setActTab] = useState('')
  const [selDomain, setSelDomain] = useState('')
  const [selModule, setSelModule] = useState('')
  const [priority, setPriority] = useState('')
  const [keyword, setKeyword] = useState('')

  // drawer
  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<any>(null)

  // batch selection
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [batchDeleting, setBatchDeleting] = useState(false)
  const [batchUpdating, setBatchUpdating] = useState(false)
  const [batchPriority, setBatchPriority] = useState('')

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }
  const toggleSelectAll = () => {
    if (selected.size === data.items.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(data.items.map((r: any) => r.id)))
    }
  }

  const doBatchDelete = async () => {
    setBatchDeleting(true)
    try {
      await batchDeleteCases(Array.from(selected))
      toast.success(`已删除 ${selected.size} 条用例`)
      setSelected(new Set())
      reload()
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
      reload()
    } catch {
      toast.error('批量更新失败')
    } finally { setBatchUpdating(false) }
  }

  // delete dialog
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  // load domains
  const loadDomains = useCallback(async () => {
    try {
      const d: any = await fetchDomains()
      setDomains(d || [])
    } catch { /* handled by interceptor */ }
  }, [])

  // load cases
  const load = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const params: any = { page, page_size: 20 }
      if (actTab) params.case_type = actTab
      if (selDomain) params.domain = selDomain
      if (selModule) params.module = selModule
      if (priority) params.priority = priority
      if (keyword) params.keyword = keyword
      const r: any = await fetchTestCases(params)
      setData(r)
    } finally { setLoading(false) }
  }, [actTab, selDomain, selModule, priority, keyword])

  useEffect(() => { loadDomains(); load() }, [loadDomains])

  const reload = () => load(data.page)

  // domain tree data
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

  // actions
  const doDelete = async (id: number) => {
    await deleteTestCase(id)
    toast.success('已删除')
    setDeleteTarget(null)
    reload()
  }

  const openEdit = (row?: any) => {
    setEditing(row || null)
    setDrawer(true)
  }

  const onSaved = () => {
    setDrawer(false)
    setEditing(null)
    reload()
    loadDomains()
  }

  const totalPages = Math.ceil(data.total / data.page_size)

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold tracking-tight">用例服务</h2>

      {/* Top Tabs */}
      <div className="flex items-center gap-2">
        {[
          ['', '全部 (901)'],
          ['manual', '功能用例 (795)'],
          ['api', '接口用例 (106)'],
        ].map(([k, label]) => (
          <button
            key={k as string}
            type="button"
            className={cn(
              'rounded-md px-4 py-1 text-sm font-medium transition-colors',
              actTab === k
                ? 'bg-accent text-accent-foreground font-semibold'
                : 'text-muted-foreground hover:text-foreground'
            )}
            onClick={() => { setActTab(k as string); load() }}
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
                if (!keys.length) { setSelDomain(''); setSelModule(''); load(); return }
                const key = keys[0]
                if (key.includes('::')) {
                  const [d, m] = key.split('::')
                  setSelDomain(d); setSelModule(m)
                } else {
                  setSelDomain(key); setSelModule('')
                }
                load()
              }}
            />
          </CardContent>
        </Card>

        {/* Right: Filter + Table */}
        <div className="flex-1 min-w-0 space-y-3">
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <Select value={selDomain || undefined} onValueChange={(v) => { setSelDomain(v || ''); setSelModule(''); load() }}>
              <SelectTrigger className="w-[130px]" size="sm">
                <SelectValue placeholder="按域筛选" />
              </SelectTrigger>
              <SelectContent>
                {domains.map((d: any) => (
                  <SelectItem key={d.domain} value={d.domain}>{d.domain}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selModule || undefined} onValueChange={(v) => { setSelModule(v || ''); load() }}>
              <SelectTrigger className="w-[150px]" size="sm">
                <SelectValue placeholder="按模块筛选" />
              </SelectTrigger>
              <SelectContent>
                {selModules.map((m: any) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={priority || undefined} onValueChange={(v) => { setPriority(v || ''); load() }}>
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
                onKeyDown={(e) => { if (e.key === 'Enter') load() }}
              />
            </InputGroup>

            <Button size="sm" onClick={() => load()}>
              <Search className="size-3.5" data-icon="inline-start" />
              搜索
            </Button>
            <Button size="sm" variant="outline" onClick={reload}>
              <RotateCcw className="size-3.5" data-icon="inline-start" />
            </Button>
            <div className="flex-1" />
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
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40px]">
                    <Checkbox
                      checked={selected.size === data.items.length && data.items.length > 0}
                      onCheckedChange={toggleSelectAll}
                    />
                  </TableHead>
                  <TableHead className="w-[160px]">编号</TableHead>
                  <TableHead>标题</TableHead>
                  <TableHead className="w-[120px]">模块</TableHead>
                  <TableHead className="w-[60px]">状态</TableHead>
                  <TableHead className="w-[140px]">API</TableHead>
                  <TableHead className="w-[120px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && data.items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                      加载中...
                    </TableCell>
                  </TableRow>
                ) : data.items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                      暂无数据
                    </TableCell>
                  </TableRow>
                ) : (
                  data.items.map((r: any) => (
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
                      <TableCell className="max-w-[140px] truncate font-mono text-xs">
                        {r.api_method ? <span>{r.api_method} {r.api_endpoint}</span> : '-'}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
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
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {data.total > 0 && (
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>共 {data.total} 条</span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page <= 1}
                  onClick={() => load(data.page - 1)}
                >
                  上一页
                </Button>
                <span className="tabular-nums">
                  {data.page} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page >= totalPages}
                  onClick={() => load(data.page + 1)}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      <CaseDrawer
        open={drawer}
        editing={editing}
        domains={domains}
        onClose={() => { setDrawer(false); setEditing(null) }}
        onSaved={onSaved}
      />
    </div>
  )
}
