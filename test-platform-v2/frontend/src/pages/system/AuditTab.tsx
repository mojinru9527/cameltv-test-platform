import { Search, RotateCcw } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import DataTable, { type DataTableColumn } from '@/components/DataTable'
import { ErrorState } from '@/components/state'
import useApi from '@/hooks/useApi'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { format } from 'date-fns'
import { useState } from 'react'
import { fetchAuditLogs } from '@/api/system'

const ACTION_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive'> = {
  'user:create': 'default',
  'user:update': 'secondary',
  'user:delete': 'destructive',
  'role:create': 'default',
  'role:update': 'secondary',
  'role:delete': 'destructive',
}

const ACTION_LABELS: Record<string, string> = {
  'user:create': '新建用户',
  'user:update': '编辑用户',
  'user:delete': '删除用户',
  'role:create': '新建角色',
  'role:update': '编辑角色',
  'role:delete': '删除角色',
}

const PAGE_SIZE = 50

export default function AuditTab() {
  const [action, setAction] = useState('')
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(0)

  const { data, isLoading, isError, error, refetch } = useApi<any>(
    () => {
      const params: any = { limit: PAGE_SIZE, offset: page * PAGE_SIZE }
      if (action) params.action = action
      if (keyword) params.keyword = keyword
      return fetchAuditLogs(params)
    },
    [action, keyword, page],
  )

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE))

  const handleSearch = () => { setPage(0) }

  const handleRefresh = () => { refetch() }

  const handleActionChange = (v: string) => {
    setAction(v === 'all' ? '' : v)
    setPage(0)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch()
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  const formatDate = (v: string) => {
    if (!v) return '-'
    try {
      return format(new Date(v), 'yyyy-MM-dd HH:mm:ss')
    } catch {
      return v
    }
  }

  // ── DataTable column definitions ──
  const auditColumns: DataTableColumn<any>[] = [
    { key: 'created_at', header: '时间', headerClassName: 'w-[170px]', render: (item) => formatDate(item.created_at) },
    { key: 'username', header: '操作人', headerClassName: 'w-[100px]', render: (item) => item.username },
    { key: 'action', header: '操作', headerClassName: 'w-[100px]', render: (item) => (
      <Badge variant={ACTION_VARIANTS[item.action] || 'outline'}>
        {ACTION_LABELS[item.action] || item.action}
      </Badge>
    )},
    { key: 'target', header: '目标', className: 'max-w-[200px] truncate', render: (item) => item.target },
    { key: 'detail', header: '详情', className: 'max-w-[200px] truncate text-muted-foreground text-xs', render: (item) => item.detail || '-' },
    { key: 'ip', header: 'IP', headerClassName: 'w-[120px]', render: (item) => item.ip },
  ]

  return (
    <div>
      {isError && (!data || (data.list && data.list.length === 0)) && (
        <ErrorState error={error} onRetry={refetch} />
      )}

      {(!isError || (data && data.list && data.list.length > 0)) && (
        <DataTable
          columns={auditColumns}
          data={data?.list ?? []}
          rowKey={(item) => item.id}
          loading={isLoading}
          loadingRows={4}
          emptyState={{ title: '暂无审计日志', description: '系统操作记录将在此显示' }}
          pagination={{
            page: page + 1,
            totalPages,
            total: data?.total ?? 0,
            onChange: (p) => handlePageChange(p - 1),
          }}
          toolbar={
            <div className="flex items-center gap-2 flex-wrap">
              <Select value={action || 'all'} onValueChange={handleActionChange}>
                <SelectTrigger className="w-[130px]" size="sm">
                  <SelectValue placeholder="操作类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部操作</SelectItem>
                  <SelectItem value="user:create">新建用户</SelectItem>
                  <SelectItem value="user:update">编辑用户</SelectItem>
                  <SelectItem value="user:delete">删除用户</SelectItem>
                  <SelectItem value="role:create">新建角色</SelectItem>
                  <SelectItem value="role:update">编辑角色</SelectItem>
                  <SelectItem value="role:delete">删除角色</SelectItem>
                </SelectContent>
              </Select>
              <Input
                placeholder="搜索目标/操作人"
                className="w-[200px]"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <Button size="sm" onClick={handleSearch}>
                <Search className="size-4" />
                搜索
              </Button>
              <Button size="sm" variant="outline" onClick={handleRefresh}>
                <RotateCcw className="size-4" />
              </Button>
            </div>
          }
        />
      )}
    </div>
  )
}
