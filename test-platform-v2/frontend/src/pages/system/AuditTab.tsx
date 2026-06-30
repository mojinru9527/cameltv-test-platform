import { Search, RotateCcw } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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
import { format } from 'date-fns'
import { useCallback, useEffect, useState } from 'react'
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
  const [data, setData] = useState({ total: 0, list: [] as any[] })
  const [loading, setLoading] = useState(false)
  const [action, setAction] = useState('')
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(0)

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE))

  const load = useCallback(async (pageNum = 0) => {
    setLoading(true)
    try {
      const params: any = { limit: PAGE_SIZE, offset: pageNum * PAGE_SIZE }
      if (action) params.action = action
      if (keyword) params.keyword = keyword
      const r: any = await fetchAuditLogs(params)
      setData(r)
    } finally {
      setLoading(false)
    }
  }, [action, keyword])

  useEffect(() => { load(0) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = () => { setPage(0); load(0) }

  const handleRefresh = () => { load(page) }

  const handleActionChange = (v: string) => {
    setAction(v === 'all' ? '' : v)
    setPage(0)
    setTimeout(() => load(0), 0)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch()
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
    load(newPage)
  }

  const formatDate = (v: string) => {
    if (!v) return '-'
    try {
      return format(new Date(v), 'yyyy-MM-dd HH:mm:ss')
    } catch {
      return v
    }
  }

  return (
    <div>
      {/* Filters */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
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

      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[170px]">时间</TableHead>
              <TableHead className="w-[100px]">操作人</TableHead>
              <TableHead className="w-[100px]">操作</TableHead>
              <TableHead>目标</TableHead>
              <TableHead>详情</TableHead>
              <TableHead className="w-[120px]">IP</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : data.list.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              data.list.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{formatDate(item.created_at)}</TableCell>
                  <TableCell>{item.username}</TableCell>
                  <TableCell>
                    <Badge variant={ACTION_VARIANTS[item.action] || 'outline'}>
                      {ACTION_LABELS[item.action] || item.action}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate">{item.target}</TableCell>
                  <TableCell className="max-w-[200px] truncate text-muted-foreground text-xs">
                    {item.detail || '-'}
                  </TableCell>
                  <TableCell>{item.ip}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-3 text-sm text-muted-foreground">
        <span>共 {data.total} 条</span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 0}
            onClick={() => handlePageChange(page - 1)}
          >
            上一页
          </Button>
          <span>
            第 {page + 1} / {totalPages} 页
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages - 1}
            onClick={() => handlePageChange(page + 1)}
          >
            下一页
          </Button>
        </div>
      </div>
    </div>
  )
}
