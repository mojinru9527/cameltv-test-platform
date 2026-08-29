import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import {
  Badge,
  Button,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchMissionRuns,
  OUTCOME_LABELS,
  RUNTIME_STATUS_LABELS,
  captureSnapshot,
  createRun,
  fetchScenarioAdapters,
  type Run,
  type Adapter,
} from '@/api/executions'
import { fetchMissionScenarios, type ScenarioRow } from '@/api/scenarios'
import { fetchCurrentContract } from '@/api/contract'
import { fetchEnvironments } from '@/api/environment'
import OutcomeBadge from '@/components/executions/OutcomeBadge'
import RuntimeStatusBadge from '@/components/executions/RuntimeStatusBadge'
import { Plus, FlaskConical, AlertTriangle } from '@/lib/icons'

const PAGE_SIZE = 20

export default function MissionExecutionsPage() {
  const { id } = useParams()
  const missionId = Number(id)
  const navigate = useNavigate()
  useDocumentTitle('执行')

  const [runs, setRuns] = useState<Run[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [outcome, setOutcome] = useState('')
  const [runtimeStatus, setRuntimeStatus] = useState('')
  const [page, setPage] = useState(1)
  const [reloadNonce, setReloadNonce] = useState(0)

  // ── Create-run dialog state ──
  const [createOpen, setCreateOpen] = useState(false)
  const [scenarios, setScenarios] = useState<ScenarioRow[]>([])
  const [environments, setEnvironments] = useState<{ id: number; name: string }[]>([])
  const [contractVersionId, setContractVersionId] = useState<number | null>(null)
  const [adapters, setAdapters] = useState<Adapter[]>([])
  const [selectedScenarioId, setSelectedScenarioId] = useState('')
  const [selectedEnvironmentId, setSelectedEnvironmentId] = useState('')
  const [selectedAdapterId, setSelectedAdapterId] = useState('')
  const [triggerType, setTriggerType] = useState('MANUAL')
  const [submitting, setSubmitting] = useState(false)

  const reload = () => setReloadNonce((n) => n + 1)

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    fetchMissionRuns(
      missionId,
      { outcome, runtime_status: runtimeStatus, page, page_size: PAGE_SIZE },
      signal,
    )
      .then((res) => {
        setRuns(res.items)
        setTotal(res.total)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId, outcome, runtimeStatus, page, reloadNonce])

  // Load create-run options once the dialog opens.
  useAbortableEffect((signal) => {
    if (!createOpen || !missionId) return
    Promise.all([
      fetchMissionScenarios(missionId).catch(() => [] as ScenarioRow[]),
      fetchEnvironments(signal).catch(() => []),
      fetchCurrentContract(missionId).catch(() => null),
    ])
      .then(([sc, envs, contract]) => {
        setScenarios(sc)
        setEnvironments(envs.map((e) => ({ id: e.id, name: e.name })))
        setContractVersionId(contract?.version?.id ?? null)
      })
      .catch(() => undefined)
  }, [createOpen, missionId])

  // Load adapters for the selected scenario.
  useAbortableEffect((signal) => {
    const sid = Number(selectedScenarioId)
    if (!sid) {
      setAdapters([])
      return
    }
    fetchScenarioAdapters(sid, signal)
      .then((res) => setAdapters(res.items))
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) setAdapters([])
      })
  }, [selectedScenarioId])

  const doCreate = async () => {
    if (submitting) return
    const scenarioId = Number(selectedScenarioId)
    const environmentId = Number(selectedEnvironmentId)
    if (!scenarioId || !environmentId) {
      toast.error('请选择场景与环境')
      return
    }
    if (!contractVersionId) {
      toast.error('请先冻结契约再创建执行')
      return
    }
    setSubmitting(true)
    try {
      const snapshot = await captureSnapshot(environmentId, missionId, {})
      await createRun(scenarioId, {
        mission_id: missionId,
        scenario_version_id: scenarioId,
        contract_version_id: contractVersionId,
        environment_id: environmentId,
        environment_snapshot_id: snapshot?.id ?? null,
        adapter_id: selectedAdapterId ? Number(selectedAdapterId) : null,
        trigger_type: triggerType,
      })
      toast.success('已创建执行')
      setCreateOpen(false)
      setSelectedScenarioId('')
      setSelectedEnvironmentId('')
      setSelectedAdapterId('')
      setPage(1)
      reload()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败')
    } finally {
      setSubmitting(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">该任务下的执行记录与结果回放。</p>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="size-4" /> 创建执行
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Select value={outcome} onValueChange={(v) => { setOutcome(v); setPage(1) }}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="全部结果" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部结果</SelectItem>
            {Object.entries(OUTCOME_LABELS).map(([key, val]) => (
              <SelectItem key={key} value={key}>
                {val.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={runtimeStatus}
          onValueChange={(v) => { setRuntimeStatus(v); setPage(1) }}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部状态</SelectItem>
            {Object.entries(RUNTIME_STATUS_LABELS).map(([key, val]) => (
              <SelectItem key={key} value={key}>
                {val.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run</TableHead>
                <TableHead>场景</TableHead>
                <TableHead>结果</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>证据</TableHead>
                <TableHead>触发</TableHead>
                <TableHead>创建时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                    <FlaskConical className="mx-auto mb-2 size-8 opacity-50" />
                    暂无执行记录。点击右上角「创建执行」开始。
                  </TableCell>
                </TableRow>
              ) : (
                runs.map((r) => (
                  <TableRow
                    key={r.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/executions/${r.id}`)}
                  >
                    <TableCell className="font-mono text-xs">#{r.id}</TableCell>
                    <TableCell className="font-mono text-xs">#{r.scenario_id}</TableCell>
                    <TableCell>
                      <OutcomeBadge outcome={r.outcome} />
                    </TableCell>
                    <TableCell>
                      <RuntimeStatusBadge status={r.runtime_status} />
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{r.evidence_status}</Badge>
                    </TableCell>
                    <TableCell>{r.trigger_type}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {r.created_at ?? '—'}
                    </TableCell>
                  </TableRow>
                ))
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
            onClick={() => setPage((p) => p - 1)}
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
            onClick={() => setPage((p) => p + 1)}
          >
            下一页
          </Button>
        </div>
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>创建执行</DialogTitle>
            <DialogDescription>
              选择场景与环境，系统将采集环境快照并启动执行。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">场景</label>
              <Select value={selectedScenarioId} onValueChange={setSelectedScenarioId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择场景" />
                </SelectTrigger>
                <SelectContent>
                  {scenarios.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">环境</label>
              <Select value={selectedEnvironmentId} onValueChange={setSelectedEnvironmentId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择环境" />
                </SelectTrigger>
                <SelectContent>
                  {environments.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">执行器（可选）</label>
              <Select value={selectedAdapterId} onValueChange={setSelectedAdapterId}>
                <SelectTrigger>
                  <SelectValue placeholder="使用默认执行器" />
                </SelectTrigger>
                <SelectContent>
                  {adapters.length === 0 ? (
                    <SelectItem value="">无可用执行器</SelectItem>
                  ) : (
                    adapters.map((a) => (
                      <SelectItem key={a.id} value={String(a.id)}>
                        {a.adapter_type} · v{a.adapter_version}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">触发方式</label>
              <Select value={triggerType} onValueChange={setTriggerType}>
                <SelectTrigger>
                  <SelectValue placeholder="触发方式" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MANUAL">手动</SelectItem>
                  <SelectItem value="SCHEDULED">定时</SelectItem>
                  <SelectItem value="RETRY">重试</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {!contractVersionId && (
              <p className="text-sm text-status-warning">
                <AlertTriangle className="size-4 inline-block" /> 契约尚未冻结，须先冻结契约才能创建执行。
              </p>
            )}
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setCreateOpen(false)} disabled={submitting}>
              取消
            </Button>
            <Button disabled={submitting || !contractVersionId} onClick={doCreate}>
              {submitting ? '创建中…' : '启动执行'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
