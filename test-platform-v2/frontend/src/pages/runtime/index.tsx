import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchWorkers,
  fetchWorkflows,
  fetchApprovals,
  fetchSecretRefs,
  fetchPolicyProfiles,
  drainWorker,
  disableWorker,
  approveApproval,
  rejectApproval,
  type WorkerNode,
  type WorkflowRun,
  type ApprovalRequest,
} from '@/api/runtime'
import { WorkerHealthTable } from './components/WorkerHealthTable'
import { WorkflowProgress } from './components/WorkflowProgress'
import { ApprovalGateCard } from './components/ApprovalGateCard'
import { KeyRound, RefreshCw } from '@/lib/icons'
import { Button as LinkButton } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth'

type Tab = 'workers' | 'workflows' | 'approvals' | 'policies' | 'secrets'

export default function RuntimeAdminPage() {
  useDocumentTitle('Durable Runtime')
  const [tab, setTab] = useState<Tab>('workers')
  const [refreshKey, setRefreshKey] = useState(0)

  const [workers, setWorkers] = useState<WorkerNode[]>([])
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([])
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const canManageTokens = useAuthStore((state) => state.hasPerm('token:manage'))

  useAbortableEffect((signal) => {
    setLoading(true)
    setLoadError('')
    Promise.all([
      fetchWorkers(signal),
      fetchWorkflows({ page: 1, page_size: 50, signal }),
      fetchApprovals(signal),
      fetchSecretRefs(signal),
      fetchPolicyProfiles(signal),
    ])
      .then(([w, wf, ap]) => {
        if (signal.aborted) return
        setWorkers(w.items)
        setWorkflows(wf.items)
        setApprovals(ap.items)
      })
      .catch((err) => {
        if (err?.code !== 'ERR_CANCELED' && !signal.aborted) {
          setLoadError(err instanceof Error ? err.message : 'Runtime 状态加载失败')
        }
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [refreshKey])

  const reload = () => setRefreshKey((k) => k + 1)

  const onDrain = async (id: number) => {
    try {
      await drainWorker(id)
      toast.success('已排空 Worker')
      reload()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '排空 Worker 失败')
    }
  }
  const onDisable = async (id: number) => {
    try {
      await disableWorker(id)
      toast.success('已禁用 Worker')
      reload()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '禁用 Worker 失败')
    }
  }
  const onApprove = async (id: number) => {
    try {
      await approveApproval(id)
      toast.success('已批准审批')
      reload()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '批准失败')
    }
  }
  const onReject = async (id: number) => {
    try {
      await rejectApproval(id)
      toast.success('已拒绝审批')
      reload()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '拒绝失败')
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <PageHeader
        title="Durable Runtime"
        description="查看平台托管的 Temporal、Worker 与安全控制状态"
      />
      {loadError && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-y border-border py-4" role="alert">
          <div>
            <p className="text-sm font-medium text-destructive">Runtime 状态加载失败</p>
            <p className="mt-1 text-sm text-muted-hc">{loadError}</p>
          </div>
          <Button variant="secondary" className="min-h-11" onClick={reload}>
            <RefreshCw className="size-4" aria-hidden="true" />
            重新检查
          </Button>
        </div>
      )}
      <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)}>
        <TabsList>
          <TabsTrigger value="workers">Worker</TabsTrigger>
          <TabsTrigger value="workflows">Workflow</TabsTrigger>
          <TabsTrigger value="approvals">审批</TabsTrigger>
          <TabsTrigger value="policies">Policy</TabsTrigger>
          <TabsTrigger value="secrets">Secret</TabsTrigger>
        </TabsList>

        <TabsContent value="workers" className="space-y-4">
          {tab === 'workers' && (
            <div className="flex flex-wrap items-center justify-between gap-3 border-y border-border py-4">
              <div className="flex min-w-0 items-start gap-2">
                <KeyRound className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <div>
                  <p className="text-sm font-medium">接入 Worker</p>
                  <p className="mt-1 text-sm text-muted-hc">
                    {canManageTokens
                      ? '生成最小权限凭据后，按一次性启动配置连接执行节点。'
                      : '请联系拥有 API Token 管理权限的管理员生成 Worker Token。'}
                  </p>
                </div>
              </div>
              {canManageTokens && (
                <LinkButton asChild className="min-h-11">
                  <Link to="/system?tab=tokens&purpose=worker">生成 Worker Token</Link>
                </LinkButton>
              )}
            </div>
          )}
          {tab === 'workers' && !loadError && (
            <WorkerHealthTable
              workers={workers}
              loading={loading}
              onDrain={onDrain}
              onDisable={onDisable}
              onRefresh={reload}
            />
          )}
        </TabsContent>

        <TabsContent value="workflows" className="space-y-4">
          {tab === 'workflows' && (loading ? (
            <p className="text-sm text-muted-foreground">加载中…</p>
          ) : workflows.length === 0 ? (
            <p className="text-sm text-muted-foreground">暂无 Workflow</p>
          ) : (
            <div className="space-y-3">
              {workflows.map((wf) => (
                <div key={wf.id} className="rounded-lg border p-4">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="font-medium">{wf.temporal_workflow_id}</span>
                    <span className="text-xs text-muted-foreground">#{wf.id}</span>
                  </div>
                  <WorkflowProgress run={wf} />
                </div>
              ))}
            </div>
          ))}
        </TabsContent>

        <TabsContent value="approvals" className="space-y-4">
          {tab === 'approvals' && (loading ? (
            <p className="text-sm text-muted-foreground">加载中…</p>
          ) : approvals.length === 0 ? (
            <p className="text-sm text-muted-foreground">暂无审批</p>
          ) : (
            <div className="space-y-3">
              {approvals.map((ap) => (
                <ApprovalGateCard key={ap.id} approval={ap} onApprove={onApprove} onReject={onReject} />
              ))}
            </div>
          ))}
        </TabsContent>

        <TabsContent value="policies" className="space-y-4">
          {tab === 'policies' && (
            <p className="text-sm text-muted-foreground">Policy Profile 列表（见 API /policy-profiles）</p>
          )}
        </TabsContent>

        <TabsContent value="secrets" className="space-y-4">
          {tab === 'secrets' && (
            <p className="text-sm text-muted-foreground">SecretRef metadata 列表（见 API /secret-refs）</p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
