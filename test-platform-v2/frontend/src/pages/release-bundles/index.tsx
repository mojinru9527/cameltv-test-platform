import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import {
  createReleaseBundle,
  deleteReleaseBundle,
  fetchReleaseBundles,
} from '@/api/releaseBundles'
import type { ReleaseBundleListItem } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
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
import { Progress } from '@/components/ui/progress'
import Pagination from '@/components/Pagination'
import PageHeader from '@/components/PageHeader'
import {
  Package,
  Plus,
  Search,
  ExternalLink,
  GitBranch,
  Layers,
  Trash2,
  Loader2,
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { AsyncState } from '@/components/state'

const STATUS_VARIANT: Record<
  string,
  { variant: 'secondary' | 'outline'; className?: string; label: string }
> = {
  draft: {
    variant: 'secondary',
    className: 'border-yellow-200 bg-yellow-50 text-yellow-700',
    label: '草稿',
  },
  active: {
    variant: 'outline',
    className: 'border-green-200 bg-green-50 text-green-700',
    label: '活跃',
  },
  archived: {
    variant: 'secondary',
    label: '已归档',
  },
}

export default function ReleaseBundlesPage() {
  useDocumentTitle('版本发布包')
  const navigate = useNavigate()

  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)

  // ── Create dialog ──
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({
    name: '',
    description: '',
    client_version: '',
    admin_version: '',
  })

  // ── Data ──
  const { data, isLoading, isError, error, refetch } = useApi(
    (signal) =>
      fetchReleaseBundles({
        keyword: keyword || undefined,
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      }),
    [keyword, statusFilter, page, pageSize],
  )

  const items = data?.items ?? []
  const total = data?.total ?? 0

  const handleCreate = async () => {
    if (!form.name.trim()) {
      toast.error('请输入发布包名称')
      return
    }
    setCreating(true)
    try {
      const created = await createReleaseBundle({
        name: form.name.trim(),
        description: form.description.trim(),
        client_version: form.client_version.trim(),
        admin_version: form.admin_version.trim(),
      })
      toast.success('创建成功')
      setCreateOpen(false)
      setForm({ name: '', description: '', client_version: '', admin_version: '' })
      refetch()
      navigate(`/release-bundles/${created.id}`)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`确定删除「${name}」？关联的模块树节点将一并删除。`)) return
    try {
      await deleteReleaseBundle(id)
      toast.success('已删除')
      refetch()
    } catch {
      // error handled by interceptor
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="版本发布包"
        description="管理蓝湖原型版本对应的发布包，构建「项目球」模块树知识图谱。"
      >
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="size-4 mr-1" />
              新建发布包
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>新建发布包</DialogTitle>
              <DialogDescription>
                一个发布包对应蓝湖更新日志中的一个版本条目，包含该版本的用户端和运营后台模块树。
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label htmlFor="rb-name">名称 *</Label>
                <Input
                  id="rb-name"
                  placeholder="如：用户端 v14.1.0 + 运营后台 v8.2.0"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="rb-client-ver">用户端版本</Label>
                  <Input
                    id="rb-client-ver"
                    placeholder="14.1.0"
                    value={form.client_version}
                    onChange={(e) =>
                      setForm({ ...form, client_version: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="rb-admin-ver">运营后台版本</Label>
                  <Input
                    id="rb-admin-ver"
                    placeholder="8.2.0"
                    value={form.admin_version}
                    onChange={(e) =>
                      setForm({ ...form, admin_version: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="rb-desc">描述</Label>
                <Input
                  id="rb-desc"
                  placeholder="可选：简要描述本版本包含的主要更新"
                  value={form.description}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setCreateOpen(false)}
                disabled={creating}
              >
                取消
              </Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating && <Loader2 className="size-4 mr-1 animate-spin" />}
                创建
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageHeader>

      {/* ── Filters ── */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            className="pl-8 h-9"
            placeholder="搜索发布包名称或版本号..."
            value={keyword}
            onChange={(e) => {
              setKeyword(e.target.value)
              setPage(1)
            }}
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={(v) => {
            setStatusFilter(v === 'all' ? '' : v)
            setPage(1)
          }}
        >
          <SelectTrigger className="h-9 w-[120px] text-xs">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="draft">草稿</SelectItem>
            <SelectItem value="active">活跃</SelectItem>
            <SelectItem value="archived">已归档</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* ── Table ── */}
      <Card>
        <CardContent className="p-0">
          <AsyncState
            isLoading={isLoading}
            isError={isError}
            error={error}
            data={items.length > 0 ? items : undefined}
            emptyTitle="暂无发布包"
            emptyDescription="点击「新建发布包」创建第一个版本"
            onRetry={refetch}
          >
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[280px]">名称</TableHead>
                  <TableHead className="w-[100px]">用户端版本</TableHead>
                  <TableHead className="w-[100px]">后台版本</TableHead>
                  <TableHead className="w-[80px]">状态</TableHead>
                  <TableHead className="w-[70px] text-center">模块</TableHead>
                  <TableHead className="w-[70px] text-center">页面</TableHead>
                  <TableHead className="w-[110px]">创建时间</TableHead>
                  <TableHead className="w-[60px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((bundle) => (
                  <TableRow
                    key={bundle.id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => navigate(`/release-bundles/${bundle.id}`)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Package className="size-4 text-muted-foreground shrink-0" />
                        <span className="font-medium truncate max-w-[220px]">
                          {bundle.name}
                        </span>
                        {bundle.parent_bundle_id && (
                          <span title="有父版本">
                            <GitBranch className="size-3 text-blue-500 shrink-0" />
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <code className="text-xs bg-muted px-1 py-0.5 rounded">
                        {bundle.client_version || '-'}
                      </code>
                    </TableCell>
                    <TableCell>
                      <code className="text-xs bg-muted px-1 py-0.5 rounded">
                        {bundle.admin_version || '-'}
                      </code>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={STATUS_VARIANT[bundle.status]?.variant ?? 'secondary'}
                        className={cn(
                          'text-[11px]',
                          STATUS_VARIANT[bundle.status]?.className,
                        )}
                      >
                        {STATUS_VARIANT[bundle.status]?.label ?? bundle.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center text-sm">
                      {bundle.module_count}
                    </TableCell>
                    <TableCell className="text-center text-sm">
                      {bundle.page_count}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {bundle.created_at
                        ? new Date(bundle.created_at).toLocaleDateString('zh-CN')
                        : '-'}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(bundle.id, bundle.name)
                        }}
                      >
                        <Trash2 className="size-4 text-muted-foreground hover:text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </AsyncState>
        </CardContent>
      </Card>

      {total > pageSize && (
        <div className="flex justify-center">
          <Pagination
            page={page}
            totalPages={Math.ceil(total / pageSize)}
            total={total}
            onChange={setPage}
          />
        </div>
      )}
    </div>
  )
}
