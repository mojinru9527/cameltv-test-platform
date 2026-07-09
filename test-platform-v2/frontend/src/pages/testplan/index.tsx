import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group'

import { Search, RotateCcw, Plus, Edit, Trash2 } from '@/lib/icons'
import DataTable, { type DataTableColumn } from '@/components/DataTable'
import PageHeader from '@/components/PageHeader'
import { deletePlan, fetchPlans } from '@/api/testplan'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { AsyncState } from '@/components/state'
import PlanDrawer from './PlanDrawer'

const STATUS_MAP: Record<string, { variant: 'outline' | 'default' | 'secondary'; className?: string; label: string }> = {
  draft: { variant: 'secondary', label: '草稿' },
  active: { variant: 'default', label: '进行中' },
  completed: { variant: 'default', className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400', label: '已完成' },
  archived: { variant: 'outline', label: '已归档' },
}

export default function TestPlanPage() {
  useDocumentTitle('测试计划')
  const navigate = useNavigate()
  const [status, setStatus] = useState('')
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [drawer, setDrawer] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  // ── Data fetching with useApi ──
  const { data, isLoading, isRefetching, isError, error, refetch } = useApi(
    () => {
      const params: any = { page, page_size: 20 }
      if (status) params.status = status
      if (keyword) params.keyword = keyword
      return fetchPlans(params) as unknown as Promise<{ total: number; items: any[]; page: number; page_size: number }>
    },
    [status, keyword, page]
  )

  const doDelete = async (id: number) => {
    await deletePlan(id)
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
  }

  const items = data?.items || []
  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1

  // ── DataTable column definitions ──
  const planColumns: DataTableColumn<any>[] = [
    { key: 'name', header: '名称', className: 'max-w-0 truncate', render: (r) => (
      <span className="font-medium text-foreground hover:underline cursor-pointer" onClick={(e) => { e.stopPropagation(); navigate(`/testplan/${r.id}`) }}>
        {r.plan_id ? <span className="text-muted-foreground mr-1.5 text-xs">{r.plan_id}</span> : null}
        {r.name}
      </span>
    )},
    { key: 'progress', header: '进度', headerClassName: 'w-[200px]', render: (r) => {
      const s = r.stats || {}
      const rate = s.total > 0 ? Math.round(((s.pass_ || 0) / s.total) * 100) : 0
      return (
        <div className="flex items-center gap-2">
          <Progress value={rate} className="flex-1 h-2" />
          <span className="text-xs text-muted-foreground whitespace-nowrap tabular-nums">
            {s.pass_ || 0}/{s.total || 0}
          </span>
        </div>
      )
    }},
    { key: 'status', header: '状态', headerClassName: 'w-[80px]', render: (r) => (
      <Badge variant={STATUS_MAP[r.status]?.variant || 'outline'} className={STATUS_MAP[r.status]?.className}>
        {STATUS_MAP[r.status]?.label || r.status}
      </Badge>
    )},
    { key: 'created_at', header: '创建时间', headerClassName: 'w-[170px]', className: 'text-muted-foreground', render: (r) => r.created_at ? new Date(r.created_at).toLocaleString() : '-' },
    { key: 'actions', header: '操作', headerClassName: 'w-[140px]', render: (r) => (
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
    )},
  ]

  return (
    <div className="space-y-4">
      <PageHeader title="测试计划" />

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={data?.items}
        onRetry={refetch}
        emptyTitle="暂无测试计划"
        emptyDescription="点击「新建计划」开始创建"
        skeletonType="table"
        loadingRows={4}
      >
        {() => (
        <DataTable
          columns={planColumns}
          data={items}
          rowKey={(r) => r.id}
          loading={isRefetching}
          loadingRows={4}
          pagination={{
            page: data?.page || 1,
            totalPages,
            total: data?.total || 0,
            onChange: (p) => setPage(p),
          }}
          onRowClick={(r) => navigate(`/testplan/${r.id}`)}
          toolbar={
          <div className="flex flex-wrap items-center gap-2">
            <Select value={status || undefined} onValueChange={(v) => { setStatus(v || ''); setPage(1) }}>
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
                onKeyDown={(e) => { if (e.key === 'Enter') { setPage(1) } }}
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
            <Button size="sm" onClick={() => openEdit()}>
              <Plus className="size-3.5" data-icon="inline-start" />
              新建计划
            </Button>
          </div>
        }
        />
        )}
      </AsyncState>

      <PlanDrawer
        open={drawer}
        editing={editing}
        onClose={() => { setDrawer(false); setEditing(null) }}
        onSaved={onSaved}
      />
    </div>
  )
}
