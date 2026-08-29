import { useCallback, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import PageHeader from '@/components/PageHeader'
import {
  Button,
  Input,
  Badge,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
} from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  fetchMissions,
  MISSION_STATUS_LABELS,
  MISSION_TYPE_LABELS,
} from '@/api/missions'
import { missionKeys } from '@/lib/queryClient'
import { Plus, Target } from '@/lib/icons'

const PAGE_SIZE = 20

export default function MissionListPage() {
  useDocumentTitle('测试任务')
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const keyword = searchParams.get('keyword') ?? ''
  const status = searchParams.get('status') ?? ''
  const page = Number(searchParams.get('page') ?? '1')

  // (v331-remediation-2 B3 / V30-100) TanStack Query：替代裸 fetch + useEffect
  const { data, isLoading } = useQuery({
    queryKey: missionKeys.list({ keyword, status, page }),
    queryFn: ({ signal }) =>
      fetchMissions({ keyword, status, page, page_size: PAGE_SIZE }, signal),
  })
  const missions = data?.items ?? []
  const total = data?.total ?? 0

  const applyFilters = useCallback(
    (next: { keyword?: string; status?: string; page?: number }) => {
      const params = new URLSearchParams(searchParams)
      if (next.keyword !== undefined) {
        if (next.keyword) params.set('keyword', next.keyword)
        else params.delete('keyword')
      }
      if (next.status !== undefined) {
        if (next.status) params.set('status', next.status)
        else params.delete('status')
      }
      if (next.page !== undefined) {
        if (next.page > 1) params.set('page', String(next.page))
        else params.delete('page')
      }
      setSearchParams(params)
    },
    [searchParams, setSearchParams],
  )

  const [keywordInput, setKeywordInput] = useState(keyword)
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total])

  return (
    <div className="space-y-4 p-4">
      <PageHeader title="测试任务" description="以 Mission 为入口回放版本测试主链">
        <Button onClick={() => navigate('/missions/new')}>
          <Plus className="size-4" /> 新建 Mission
        </Button>
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="w-64"
          placeholder="搜索标题 / 任务编号"
          aria-label="搜索标题或任务编号"
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') applyFilters({ keyword: keywordInput, page: 1 })
          }}
        />
        <Select value={status} onValueChange={(v) => applyFilters({ status: v, page: 1 })}>
          <SelectTrigger className="w-56" aria-label="按状态筛选">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部状态</SelectItem>
            {Object.entries(MISSION_STATUS_LABELS).map(([key, val]) => (
              <SelectItem key={key} value={key}>
                {val.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="secondary"
          onClick={() => applyFilters({ keyword: keywordInput, page: 1 })}
        >
          查询
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2" role="status" aria-busy="true" aria-label="加载中">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>任务编号</TableHead>
                <TableHead>标题</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>版本</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>验收</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {missions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                    <Target className="mx-auto mb-2 size-8 opacity-50" />
                    暂无测试任务。点击右上角「新建 Mission」开始。
                  </TableCell>
                </TableRow>
              ) : (
                missions.map((m) => {
                  const statusMeta = MISSION_STATUS_LABELS[m.status]
                  // V30-109 keyboard：行点击打开同时支持 Enter/Space 键盘触发
                  const openMission = () => navigate(`/missions/${m.id}/overview`)
                  return (
                    <TableRow
                      key={m.id}
                      className="cursor-pointer"
                      tabIndex={0}
                      aria-label={`打开测试任务 ${m.title}`}
                      onClick={openMission}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          openMission()
                        }
                      }}
                    >
                      <TableCell className="font-mono text-xs">{m.mission_key}</TableCell>
                      <TableCell className="font-medium">{m.title}</TableCell>
                      <TableCell>{MISSION_TYPE_LABELS[m.mission_type] ?? m.mission_type}</TableCell>
                      <TableCell>{m.version_label ?? '—'}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={statusMeta?.color}>
                          {statusMeta?.label ?? m.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{m.acceptance_status}</Badge>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">共 {total} 条</span>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={page <= 1}
            onClick={() => applyFilters({ page: page - 1 })}
          >
            上一页
          </Button>
          <span>
            {page} / {totalPages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => applyFilters({ page: page + 1 })}
          >
            下一页
          </Button>
        </div>
      </div>
    </div>
  )
}
