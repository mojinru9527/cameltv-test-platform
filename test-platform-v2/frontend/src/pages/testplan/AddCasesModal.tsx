import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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

import { Search } from '@/lib/icons'
import { addCasesToPlan } from '@/api/testplan'
import { fetchDomains, fetchTestCases } from '@/api/testcase'

interface Props {
  open: boolean
  planId: number
  onClose: () => void
  onAdded: () => void
}

const PRIORITY_BADGES: Record<string, 'default' | 'destructive' | 'secondary' | 'outline'> = {
  P0: 'destructive', P1: 'secondary', P2: 'default', P3: 'outline',
}

export default function AddCasesModal({ open, planId, onClose, onAdded }: Props) {
  const [domains, setDomains] = useState<any[]>([])
  const [data, setData] = useState({ total: 0, items: [] as any[], page: 1, page_size: 10 })
  const [loading, setLoading] = useState(false)
  const [adding, setAdding] = useState(false)
  const [selDomain, setSelDomain] = useState('')
  const [selModule, setSelModule] = useState('')
  const [keyword, setKeyword] = useState('')
  const [selRowKeys, setSelRowKeys] = useState<number[]>([])

  const loadDomains = useCallback(async () => {
    try {
      const d: any = await fetchDomains()
      setDomains(d || [])
    } catch { /* */ }
  }, [])

  const load = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const params: any = { page, page_size: 10 }
      if (selDomain) params.domain = selDomain
      if (selModule) params.module = selModule
      if (keyword) params.keyword = keyword
      const r: any = await fetchTestCases(params)
      setData(r)
    } finally { setLoading(false) }
  }, [selDomain, selModule, keyword])

  useEffect(() => { if (open) { loadDomains(); load() } }, [open, loadDomains])

  const domainTree = useMemo(() => {
    return domains.map((d: any) => ({
      title: <span className="text-xs">{d.domain} <span className="text-muted-foreground">({d.count})</span></span>,
      key: d.domain,
      children: d.modules?.map((m: any) => ({
        title: <span className="text-xs">{m.module} <span className="text-muted-foreground">({m.count})</span></span>,
        key: `${d.domain}::${m.module}`,
        isLeaf: true,
      })) || [],
    }))
  }, [domains])

  const selModules = useMemo(() => {
    if (!selDomain) return []
    const d = domains.find((x: any) => x.domain === selDomain)
    return d?.modules?.map((m: any) => ({ value: m.module, label: `${m.module} (${m.count})` })) || []
  }, [selDomain, domains])

  const doAdd = async () => {
    if (!selRowKeys.length) { toast.warning('请选择用例'); return }
    setAdding(true)
    try {
      const r: any = await addCasesToPlan(planId, selRowKeys)
      toast.success(`已添加 ${r.added} 条用例`)
      setSelRowKeys([])
      onAdded()
      onClose()
    } catch {
      // handled by interceptor
    } finally { setAdding(false) }
  }

  const toggleAll = (checked: boolean) => {
    if (checked) {
      setSelRowKeys(data.items.map((r: any) => r.id))
    } else {
      setSelRowKeys([])
    }
  }

  const toggleRow = (id: number) => {
    setSelRowKeys((prev) =>
      prev.includes(id) ? prev.filter((k) => k !== id) : [...prev, id]
    )
  }

  const allChecked = data.items.length > 0 && data.items.every((r: any) => selRowKeys.includes(r.id))
  const totalPages = Math.ceil(data.total / data.page_size)

  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-[860px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>添加用例到计划</DialogTitle>
          <DialogDescription>选择要添加到当前计划的测试用例</DialogDescription>
        </DialogHeader>

        <div className="flex gap-3 flex-1 min-h-0">
          {/* Left: Domain Tree */}
          <div className="w-[180px] shrink-0 border-r pr-3 overflow-y-auto">
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
          </div>

          {/* Right: Filters + Table */}
          <div className="flex-1 min-w-0 space-y-3">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2">
              <Select value={selDomain || undefined} onValueChange={(v) => { setSelDomain(v || ''); setSelModule(''); load() }}>
                <SelectTrigger className="w-[110px]" size="sm">
                  <SelectValue placeholder="域" />
                </SelectTrigger>
                <SelectContent>
                  {domains.map((d: any) => (
                    <SelectItem key={d.domain} value={d.domain}>{d.domain}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={selModule || undefined} onValueChange={(v) => { setSelModule(v || ''); load() }}>
                <SelectTrigger className="w-[130px]" size="sm">
                  <SelectValue placeholder="模块" />
                </SelectTrigger>
                <SelectContent>
                  {selModules.map((m: any) => (
                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <InputGroup className="w-[180px]">
                <InputGroupAddon>
                  <Search className="size-3.5" />
                </InputGroupAddon>
                <InputGroupInput
                  placeholder="搜索标题"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') load() }}
                />
              </InputGroup>
            </div>

            {/* Table */}
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">
                      <Checkbox
                        checked={allChecked}
                        onCheckedChange={toggleAll}
                        aria-label="全选"
                      />
                    </TableHead>
                    <TableHead>标题</TableHead>
                    <TableHead className="w-[100px]">模块</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading && data.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} className="h-24 text-center text-muted-foreground">
                        加载中...
                      </TableCell>
                    </TableRow>
                  ) : data.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} className="h-24 text-center text-muted-foreground">
                        暂无数据
                      </TableCell>
                    </TableRow>
                  ) : (
                    data.items.map((r: any) => (
                      <TableRow key={r.id}>
                        <TableCell>
                          <Checkbox
                            checked={selRowKeys.includes(r.id)}
                            onCheckedChange={() => toggleRow(r.id)}
                            aria-label={`选择 ${r.title}`}
                          />
                        </TableCell>
                        <TableCell className="max-w-0 truncate">
                          <div className="flex items-center gap-1">
                            <Badge variant={PRIORITY_BADGES[r.priority] || 'outline'}>{r.priority}</Badge>
                            {r.case_type === 'api' && (
                              <Badge variant="secondary" className="bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                                接口
                              </Badge>
                            )}
                            <span className="truncate">{r.title}</span>
                          </div>
                        </TableCell>
                        <TableCell className="max-w-[100px] truncate">{r.module}</TableCell>
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

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>取消</Button>
          <Button disabled={adding} onClick={doAdd}>
            添加选中 ({selRowKeys.length})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
