import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { ArrowRight, Plus } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  PageShell,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/ui'
import DataTable, { type DataTableColumn } from '@/components/DataTable'
import SearchInput from '@/components/SearchInput'
import { ErrorState } from '@/components/state'
import { useApi } from '@/hooks/useApi'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { listVersionTasks, type VersionTask, type VersionTaskPage } from '@/api/versionTask'
import { TASK_STATUS_LABEL, TASK_STATUS_TONE, VERDICT_LABEL } from './statusLabels'

const PAGE_SIZE = 20
/** Radix Select 不接受空字符串作为 value，用哨兵表示「不筛选」。 */
const ALL_STATUS = '__all__'

function coverageText(coverage: Record<string, unknown>): string {
  const num = (key: string) => Number(coverage?.[key]) || 0
  const total = num('pass') + num('fail') + num('skip') + num('blocked')
  return total ? `${num('pass')}/${total}` : '—'
}

/** 版本验收任务列表（DEF-20260905-002）：任务创建后唯一可达的跟踪入口。 */
export default function VersionTaskListPage() {
  useDocumentTitle('版本验收任务')
  const navigate = useNavigate()

  const [status, setStatus] = useState(ALL_STATUS)
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const debouncedKeyword = useDebouncedValue(keyword, 300)

  const { data, isLoading, isError, error, refetch } = useApi<VersionTaskPage>(
    (signal) =>
      listVersionTasks(
        status === ALL_STATUS ? '' : status,
        debouncedKeyword,
        signal,
        page,
        PAGE_SIZE,
      ),
    { deps: [status, debouncedKeyword, page], showErrorToast: false },
  )

  const items = useMemo(() => data?.items ?? [], [data])
  const total = data?.total ?? 0

  const columns: DataTableColumn<VersionTask>[] = [
    {
      key: 'title',
      header: '标题',
      render: (row) => (
        <span className="block max-w-[24rem] truncate" title={row.title}>
          {row.title}
        </span>
      ),
    },
    {
      key: 'version',
      header: '版本',
      width: '110px',
      render: (row) => <Badge tone="neutral">{row.version}</Badge>,
    },
    {
      key: 'status',
      header: '状态',
      width: '110px',
      render: (row) => (
        <Badge tone={TASK_STATUS_TONE[row.status] ?? 'neutral'}>
          {TASK_STATUS_LABEL[row.status] ?? row.status}
        </Badge>
      ),
    },
    {
      key: 'verdict',
      header: '结论',
      width: '110px',
      render: (row) => (row.verdict ? VERDICT_LABEL[row.verdict] ?? row.verdict : '—'),
    },
    {
      key: 'coverage',
      header: '覆盖',
      width: '90px',
      render: (row) => coverageText(row.coverage),
    },
    {
      key: 'updated_at',
      header: '更新时间',
      width: '150px',
      render: (row) => (row.updated_at ? new Date(row.updated_at).toLocaleString('zh-CN') : '—'),
    },
    {
      key: 'actions',
      header: '操作',
      width: '80px',
      render: (row) => (
        // stopPropagation 挂在 Link 上：既阻止冒泡到 onRowClick（否则一次点击
        // 压两条历史），又不影响 React Router 自身的导航。
        <Link
          to={`/version-tasks/${row.id}`}
          className="ml-auto inline-flex"
          aria-label={`查看 ${row.title} 的执行与证据`}
          onClick={(event) => event.stopPropagation()}
        >
          <Button size="sm" variant="ghost" className="h-8" tabIndex={-1}>
            详情
            <ArrowRight className="size-4" aria-hidden="true" />
          </Button>
        </Link>
      ),
    },
  ]

  return (
    <PageShell
      title="版本验收任务"
      description="跟踪每个版本的方案评审、执行证据与放行结论。"
      glass
    >
      <Card>
        <CardContent>
          {isError ? (
            <ErrorState
              title="版本验收任务加载失败"
              error={error}
              onRetry={refetch}
              secondaryAction={{ label: '返回工作台', onClick: () => navigate('/workbench') }}
            />
          ) : (
            <DataTable<VersionTask>
              columns={columns}
              data={items}
              rowKey={(row) => row.id}
              loading={isLoading}
              onRowClick={(row) => navigate(`/version-tasks/${row.id}`)}
              ariaLabel="版本验收任务列表"
              emptyState={{
                title: '暂无版本验收任务',
                description: '创建任务后可在此跟踪方案评审、执行与放行结论。',
                action: { label: '新建版本任务', onClick: () => navigate('/version-tasks/new') },
              }}
              toolbar={
                <div className="flex flex-wrap items-center gap-2">
                  <Select
                    value={status}
                    onValueChange={(value) => {
                      setStatus(value)
                      setPage(1)
                    }}
                  >
                    <SelectTrigger className="h-9 w-[130px]" aria-label="按状态筛选">
                      <SelectValue placeholder="全部状态" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={ALL_STATUS}>全部状态</SelectItem>
                      {Object.entries(TASK_STATUS_LABEL).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <SearchInput
                    value={keyword}
                    onChange={(value) => {
                      setKeyword(value)
                      setPage(1)
                    }}
                    placeholder="搜索标题或版本"
                    inputClassName="h-9 w-[220px]"
                    showButton={false}
                    clearable
                  />
                  <Link to="/version-tasks/new" className="ml-auto" aria-label="新建版本任务">
                    <Button variant="primary" size="lg" tabIndex={-1}>
                      <Plus className="size-4" aria-hidden="true" />
                      新建版本任务
                    </Button>
                  </Link>
                </div>
              }
              pagination={
                total > PAGE_SIZE
                  ? {
                      page,
                      totalPages: Math.max(1, Math.ceil(total / PAGE_SIZE)),
                      total,
                      onChange: setPage,
                    }
                  : undefined
              }
            />
          )}
        </CardContent>
      </Card>
    </PageShell>
  )
}
