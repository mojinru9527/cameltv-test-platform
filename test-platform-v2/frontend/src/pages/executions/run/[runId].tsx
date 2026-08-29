import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchRun,
  fetchRunAssertions,
  fetchRunEvidence,
  fetchRunSteps,
  fetchLatestSnapshot,
  retryRun,
  cancelRun,
  finishRun,
  type Run,
  type Step,
  type Assertion,
  type Evidence,
  type EnvironmentSnapshot,
} from '@/api/executions'
import OutcomeBadge from '@/components/executions/OutcomeBadge'
import RuntimeStatusBadge from '@/components/executions/RuntimeStatusBadge'
import LegacyExecutionBadge from '@/components/executions/LegacyExecutionBadge'
import ExecutionTimeline from '@/components/executions/ExecutionTimeline'
import AssertionSummary from '@/components/executions/AssertionSummary'
import RequiredOracleList from '@/components/executions/RequiredOracleList'
import EvidenceList from '@/components/executions/EvidenceList'
import WhyPassPanel from '@/components/executions/WhyPassPanel'
import FailureClassificationPanel from '@/components/executions/FailureClassificationPanel'
import EnvironmentSnapshotCard from '@/components/executions/EnvironmentSnapshotCard'
import ShadowAuditPanel from '@/components/executions/ShadowAuditPanel'
import { ArrowLeft, History, RotateCcw } from '@/lib/icons'

export default function RunDetailPage() {
  const { runId: rawRunId } = useParams()
  const runId = Number(rawRunId)
  const navigate = useNavigate()
  useDocumentTitle(runId ? `Run #${runId}` : '执行详情')

  const [run, setRun] = useState<Run | null>(null)
  const [steps, setSteps] = useState<Step[]>([])
  const [assertions, setAssertions] = useState<Assertion[]>([])
  const [evidence, setEvidence] = useState<Evidence[]>([])
  const [snapshot, setSnapshot] = useState<EnvironmentSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(false)
  const [reloadNonce, setReloadNonce] = useState(0)

  const reload = () => setReloadNonce((n) => n + 1)

  useAbortableEffect((signal) => {
    if (!runId) return
    setLoading(true)
    Promise.all([
      fetchRun(runId, signal),
      fetchRunSteps(runId, signal).catch(() => ({ items: [] })),
      fetchRunAssertions(runId, signal).catch(() => ({ items: [] })),
      fetchRunEvidence(runId, signal).catch(() => ({ items: [] })),
    ])
      .then(([r, stepsRes, assertionRes, evidenceRes]) => {
        setRun(r)
        setSteps(stepsRes.items)
        setAssertions(assertionRes.items)
        setEvidence(evidenceRes.items)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [runId, reloadNonce])

  useAbortableEffect((signal) => {
    if (!run?.environment_id || !run.mission_id) return
    fetchLatestSnapshot(run.environment_id, run.mission_id, signal)
      .then((snap) => setSnapshot(snap ?? null))
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) setSnapshot(null)
      })
  }, [run?.environment_id, run?.mission_id])

  const doRetry = async () => {
    if (acting) return
    setActing(true)
    try {
      await retryRun(runId)
      toast.success('已发起重试')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '重试失败')
    } finally {
      setActing(false)
    }
  }

  const doCancel = async () => {
    if (acting) return
    setActing(true)
    try {
      await cancelRun(runId)
      toast.success('已取消执行')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '取消失败')
    } finally {
      setActing(false)
    }
  }

  const doFinish = async () => {
    if (acting) return
    setActing(true)
    try {
      await finishRun(runId)
      toast.success('已结算执行结果')
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '结算失败')
    } finally {
      setActing(false)
    }
  }

  if (loading && !run) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-32 w-full" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      </div>
    )
  }

  if (!run) {
    return (
      <div className="p-10 text-center text-muted-foreground">
        执行记录不存在或已被删除。
      </div>
    )
  }

  const canCancel = !['FINISHED', 'CANCELLED'].includes(run.runtime_status)
  const canFinish = run.runtime_status === 'RUNNING'

  return (
    <div className="space-y-4 p-4">
      <div>
        <Button variant="ghost" size="sm" onClick={() => navigate('/executions')}>
          <ArrowLeft className="size-4" /> 返回执行中心
        </Button>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-xl font-semibold tracking-[-0.02em]">Run #{run.id}</h1>
          <OutcomeBadge outcome={run.outcome} />
          <RuntimeStatusBadge status={run.runtime_status} />
          <LegacyExecutionBadge
            legacy={run.trigger_type === 'LEGACY' || run.trigger_type === 'MIGRATED'}
          />
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>场景 #{run.scenario_id}</span>
          <span>· 任务 #{run.mission_id}</span>
          <span>· 环境 #{run.environment_id}</span>
          <span>· 触发 {run.trigger_type}</span>
          <span>· 重试 {run.retry_no}</span>
          <span>· 创建 {run.created_at ?? '—'}</span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" onClick={() => navigate(`/executions/${run.id}/replay`)}>
            <History className="size-4" /> 回放
          </Button>
          <Button size="sm" variant="secondary" disabled={acting} onClick={doRetry}>
            <RotateCcw className="size-4" /> 重试
          </Button>
          {canCancel && (
            <Button size="sm" variant="ghost" disabled={acting} onClick={doCancel}>
              取消
            </Button>
          )}
          {canFinish && (
            <Button size="sm" disabled={acting} onClick={doFinish}>
              完成结算
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">判定</CardTitle>
          </CardHeader>
          <CardContent>
            {run.outcome === 'PASS' ? (
              <WhyPassPanel run={run} assertions={assertions} steps={steps} evidence={evidence} />
            ) : run.outcome ? (
              <FailureClassificationPanel run={run} steps={steps} assertions={assertions} />
            ) : (
              <p className="text-sm text-muted-foreground">尚未结算结果。</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">环境快照</CardTitle>
          </CardHeader>
          <CardContent>
            <EnvironmentSnapshotCard snapshot={snapshot} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">断言汇总</CardTitle>
          </CardHeader>
          <CardContent>
            <AssertionSummary assertions={assertions} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">必需 Oracle</CardTitle>
          </CardHeader>
          <CardContent>
            <RequiredOracleList assertions={assertions} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">证据清单</CardTitle>
          </CardHeader>
          <CardContent>
            <EvidenceList evidence={evidence} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-base">执行步骤</CardTitle>
          </CardHeader>
          <CardContent>
            <ExecutionTimeline steps={steps} />
          </CardContent>
        </Card>

        <ShadowAuditPanel runId={run.id} />
      </div>
    </div>
  )
}
