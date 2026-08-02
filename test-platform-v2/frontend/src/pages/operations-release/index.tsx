import { useState } from 'react'
import { Badge, Button } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AsyncState } from '@/components/state'
import { fetchOpsDeploymentEvents, fetchOpsDeployments, type OpsDeployment } from '@/api/opsReleases'
import { useApi } from '@/hooks/useApi'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { AlertTriangle, Clock, RefreshCw, ShieldCheck } from '@/lib/icons'

const STATE_LABEL: Record<string, string> = {
  DRAFT: '草稿',
  VALIDATED: '已校验',
  TEST_DEPLOYING: '测试环境部署中',
  TEST_VERIFYING: '测试验证中',
  TEST_VERIFIED: '测试已验证',
  TEST_FAILED: '测试失败',
  TEST_ROLLING_BACK: '测试环境回滚中',
  TEST_ROLLED_BACK: '测试环境已回滚',
}

function stateVariant(state: string): 'secondary' | 'outline' | 'destructive' {
  if (state === 'TEST_FAILED') return 'destructive'
  if (state === 'TEST_VERIFIED' || state === 'TEST_ROLLED_BACK') return 'outline'
  return 'secondary'
}

function DeploymentRow({ deployment, selected, onSelect }: {
  deployment: OpsDeployment
  selected: boolean
  onSelect: (deployment: OpsDeployment) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(deployment)}
      aria-label={`查看发布记录 ${deployment.release_id}`}
      className={`min-h-11 w-full rounded-md border p-3 text-left transition-colors ${
        selected ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/60'
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{deployment.release_id}</span>
        <Badge variant={stateVariant(deployment.state)}>{STATE_LABEL[deployment.state] ?? deployment.state}</Badge>
        <span className="text-xs text-muted-foreground">{deployment.environment}</span>
      </div>
      <p className="mt-1 truncate font-mono text-[11px] text-muted-foreground" title={deployment.manifest_sha256}>
        Manifest {deployment.manifest_sha256}
      </p>
    </button>
  )
}

export default function OperationsReleasePage() {
  useDocumentTitle('运维发布控制')
  const [selected, setSelected] = useState<OpsDeployment | null>(null)
  const deployments = useApi(
    (signal) => fetchOpsDeployments(signal),
    { deps: [], showErrorToast: false },
  )
  const events = useApi(
    (signal) => selected ? fetchOpsDeploymentEvents(selected.id, signal) : Promise.resolve([]),
    { deps: [selected?.id], initialData: [], showErrorToast: false },
  )

  const choose = (deployment: OpsDeployment) => setSelected(deployment)

  return (
    <div className="space-y-4">
      <PageHeader
        title="运维发布控制"
        icon={ShieldCheck}
        description="只读展示独立发布控制面已持久化的发布事实；生产发布尚未配置。"
      >
        <Button variant="secondary" size="sm" onClick={deployments.refetch} disabled={deployments.isLoading || deployments.isRefetching}>
          <RefreshCw className={`mr-1 size-4 ${deployments.isRefetching ? 'animate-spin' : ''}`} />
          刷新记录
        </Button>
      </PageHeader>

      <Card className="border-status-warning-border bg-status-warning-muted">
        <CardContent className="flex gap-2 p-3 text-sm text-status-warning">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
          <p>生产发布、生产数据库迁移和外部执行器均未配置。此页面没有发布、审批或回滚操作入口。</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base">发布记录</CardTitle></CardHeader>
          <CardContent>
            <AsyncState
              isLoading={deployments.isLoading}
              isError={deployments.isError}
              error={deployments.error}
              data={deployments.data}
              onRetry={deployments.refetch}
              emptyTitle="暂无已持久化发布记录"
              emptyDescription="需由受控发布执行器登记测试环境发布后，才会在此显示。"
            >
              {(items) => <div className="space-y-2">{items.map((item) => <DeploymentRow key={item.id} deployment={item} selected={item.id === selected?.id} onSelect={choose} />)}</div>}
            </AsyncState>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base">事件时间线</CardTitle></CardHeader>
          <CardContent>
            {!selected ? (
              <p className="text-sm text-muted-foreground">选择一条发布记录以查看后端返回的有序审计事件。</p>
            ) : (
              <AsyncState
                isLoading={events.isLoading}
                isError={events.isError}
                error={events.error}
                data={events.data}
                onRetry={events.refetch}
                emptyTitle="暂无审计事件"
                emptyDescription="该记录尚未写入可展示的发布状态变化。"
              >
                {(items) => <ol className="space-y-3">{items.map((event) => <li key={event.sequence} className="border-l-2 border-primary/40 pl-3"><div className="flex items-center gap-2"><Badge variant="secondary">#{event.sequence}</Badge><span className="text-sm font-medium">{STATE_LABEL[event.to_state] ?? event.to_state}</span></div><p className="mt-1 text-sm text-muted-foreground">{event.reason}</p><p className="mt-1 flex items-center gap-1 text-[11px] text-muted-foreground"><Clock className="size-3" aria-hidden />{event.phase} · {event.actor} · {new Date(event.created_at).toLocaleString('zh-CN')}</p></li>)}</ol>}
              </AsyncState>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
