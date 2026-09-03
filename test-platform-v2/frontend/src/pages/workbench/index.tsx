import { Link } from 'react-router'
import { useMemo } from 'react'
import { ClipboardCheck, Gauge, AlertCircle, FileCheck, ArrowRight, Inbox } from '@/lib/icons'
import PageHeader from '@/components/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AsyncState } from '@/components/state'
import PageIntro from '@/components/foolproof/PageIntro'
import TermTip from '@/components/foolproof/TermTip'
import { Button } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { useApi } from '@/hooks/useApi'
import { fetchDashboardTodo } from '@/api/dashboard'
import type { DashboardTodo, TodoBucket } from '@/types'

interface TodoPanelProps {
  title: string
  description: string
  icon: React.ReactNode
  accent?: 'primary' | 'danger' | 'muted'
  bucket: TodoBucket
  emptyText: string
  viewAll: string
}

function accentClass(accent: TodoPanelProps['accent']): string {
  if (accent === 'danger') return 'text-destructive'
  if (accent === 'muted') return 'text-muted-foreground'
  return 'text-primary'
}

function TodoPanel({ title, description, icon, accent, bucket, emptyText, viewAll }: TodoPanelProps) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          {icon}
          <span className={accentClass(accent)}>{title}</span>
          <span className="text-xs font-normal text-muted-foreground">{description}</span>
          <Badge variant="secondary" className="ml-auto">{bucket.count}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {bucket.items.length === 0 ? (
          <div className="flex items-center gap-2 rounded-md border border-dashed px-3 py-4 text-xs text-muted-foreground">
            <Inbox className="size-4 shrink-0" />
            <span>{emptyText}</span>
          </div>
        ) : (
          <>
            {bucket.items.map((item) => (
              <Link
                key={item.id}
                to={item.link}
                className="group flex min-h-[40px] items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted"
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium text-foreground">{item.title}</span>
                  <span className="block truncate text-xs text-muted-foreground">{item.subtitle}</span>
                </span>
                <ArrowRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
              </Link>
            ))}
            <Link to={viewAll} className="inline-flex items-center gap-1 px-2 pt-1 text-xs text-primary hover:underline">
              查看全部
            </Link>
          </>
        )}
      </CardContent>
    </Card>
  )
}

export default function Workbench() {
  useDocumentTitle('我的待办')
  const { data, isLoading, isError, error, refetch } = useApi<DashboardTodo>(
    (signal) => fetchDashboardTodo(signal),
  )

  const panels = useMemo(() => {
    if (!data) return []
    return [
      {
        key: 'reviews',
        title: '待审',
        icon: <ClipboardCheck className="size-4 text-primary" />,
        description: 'AI 生成用例待审核',
        accent: 'primary' as const,
        bucket: data.reviews,
        emptyText: '暂无待审核用例',
        viewAll: '/requirement',
      },
      {
        key: 'running',
        title: '在跑',
        icon: <Gauge className="size-4 text-muted-foreground" />,
        description: '后台 AI 任务进行中',
        accent: 'muted' as const,
        bucket: data.running,
        emptyText: '暂无进行中任务',
        viewAll: '/report',
      },
      {
        key: 'failures',
        title: '失败 / 需关注',
        icon: <AlertCircle className="size-4 text-destructive" />,
        description: '执行失败与未关闭缺陷',
        accent: 'danger' as const,
        bucket: data.failures,
        emptyText: '暂无失败项',
        viewAll: '/defect',
      },
      {
        key: 'releases',
        title: '待放行',
        icon: <FileCheck className="size-4 text-primary" />,
        description: '当前版本发布包',
        accent: 'primary' as const,
        bucket: data.releases,
        emptyText: '暂无待放行版本',
        viewAll: '/release-bundles',
      },
    ]
  }, [data])

  return (
    <div className="space-y-4">
      <PageHeader title="我的待办" description="今天要审什么、什么在跑、什么失败、哪个版本待放行" />
      <PageIntro
        title="工作台 = 我的待办"
        description={
          '这个页面回答「今天我该干嘛」：待审的用例、在跑的任务、失败项、待放行的版本。点进「一次执行」看证据。'
        }
      />
      <div className="flex flex-wrap items-center gap-2">
        <TermTip term="run" />
        <Link to="/version-tasks"><Button size="sm" variant="primary">创建版本任务</Button></Link>
      </div>
      <AsyncState
        isLoading={isLoading}
        isError={isError}
        error={error}
        data={data}
        onRetry={refetch}
        loadingText="正在加载我的待办"
        skeletonType="card"
        loadingRows={4}
      >
        {() => (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {panels.map((p) => (
              <TodoPanel
                key={p.key}
                title={p.title}
                description={p.description}
                icon={p.icon}
                accent={p.accent}
                bucket={p.bucket}
                emptyText={p.emptyText}
                viewAll={p.viewAll}
              />
            ))}
          </div>
        )}
      </AsyncState>
    </div>
  )
}
