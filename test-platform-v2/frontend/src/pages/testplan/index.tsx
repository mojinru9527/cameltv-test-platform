import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
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

import { Search, RotateCcw, Plus, Edit, Trash2 } from '@/lib/icons'
import { deletePlan, fetchPlans } from '@/api/testplan'
import PlanDrawer from './PlanDrawer'

const STATUS_MAP: Record<string, { variant: 'outline' | 'default' | 'secondary'; className?: string; label: string }> = {
  draft: { variant: 'secondary', label: '草稿' },
  active: { variant: 'default', label: '进行中' },
  completed: { variant: 'default', className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400', label: '已完成' },
  archived: { variant: 'outline', label: '已归档' },
}

export default function TestPlanPage() {
  const navigate = useNavigate()
  const [data, setData] = useState({ total: 0, items: [] as any[], page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [keyword, setKeyword] = useState('')
  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  const load = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const params: any = { page, page_size: 20 }
      if (status) params.status = status
      if (keyword) params.keyword = keyword
      const r: any = await fetchPlans(params)
      setData(r)
    } finally { setLoading(false) }
  }, [status, keyword])

  useEffect(() => { load() }, [load])

  const doDelete = async (id: number) => {
    await deletePlan(id)
    toast.success('已删除')
    setDeleteTarget(null)
    load()
  }

  const openEdit = (row?: any) => {
    setEditing(row || null)
    setDrawer(true)
  }

  const onSaved = () => {
    setDrawer(false)
    setEditing(null)
    load()
  }

  const totalPages = Math.ceil(data.total / data.page_size)

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold tracking-tight">测试计划</h2>

      {/* Filter Card */}
      <Card size="sm">
        <CardContent className="pt-[var(--card-spacing)]">
          <div className="flex flex-wrap items-center gap-2">
            <Select value={status || undefined} onValueChange={(v) => { setStatus(v || ''); load() }}>
              <SelectTrigger className="w-[120px]" size="sm">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_MAP && Object.keys(STATUS_MAP).length > 0
                  ? Object.entries(STATUS_MAP).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v.label}</SelectItem>
                    ))
                  : null}
              </SelectContent>
            </Select>

            <InputGroup className="w-[220px]">
              <InputGroupAddon>
                <Search className="size-3.5" />
              </InputGroupAddon>
              <InputGroupInput
                placeholder="搜索计划名称"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') load() }}
              />
            </InputGroup>

            <Button size="sm" onClick={() => load()}>
              <Search className="size-3.5" data-icon="inline-start" />
              搜索
            </Button>
            <Button size="sm" variant="outline" onClick={() => load(data.page)}>
              <RotateCcw className="size-3.5" data-icon="inline-start" />
            </Button>
            <div className="flex-1" />
            <Button size="sm" onClick={() => openEdit()}>
              <Plus className="size-3.5" data-icon="inline-start" />
              新建计划
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead>
              <TableHead className="w-[200px]">进度</TableHead>
              <TableHead className="w-[80px]">状态</TableHead>
              <TableHead className="w-[170px]">创建时间</TableHead>
              <TableHead className="w-[140px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && data.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                  加载中...
                </TableCell>
              </TableRow>
            ) : data.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              data.items.map((r: any) => {
                const s = r.stats || {}
                const rate = s.total > 0 ? Math.round(((s.pass_ || 0) / s.total) * 100) : 0
                return (
                  <TableRow key={r.id} className="cursor-pointer" onClick={() => navigate(`/testplan/${r.id}`)}>
                    <TableCell className="max-w-0 truncate">
                      <span className="font-medium text-foreground hover:underline cursor-pointer"
                        onClick={(e) => { e.stopPropagation(); navigate(`/testplan/${r.id}`) }}>
                        {r.plan_id ? (
                          <span className="text-muted-foreground mr-1.5 text-xs">{r.plan_id}</span>
                        ) : null}
                        {r.name}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={rate} className="flex-1 h-2" />
                        <span className="text-xs text-muted-foreground whitespace-nowrap tabular-nums">
                          {s.pass_ || 0}/{s.total || 0}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_MAP[r.status]?.variant || 'outline'} className={STATUS_MAP[r.status]?.className}>
                        {STATUS_MAP[r.status]?.label || r.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {r.created_at ? new Date(r.created_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
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
                )
              })
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

      <PlanDrawer
        open={drawer}
        editing={editing}
        onClose={() => { setDrawer(false); setEditing(null) }}
        onSaved={onSaved}
      />
    </div>
  )
}
