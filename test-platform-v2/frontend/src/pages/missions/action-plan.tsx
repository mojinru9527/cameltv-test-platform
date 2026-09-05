import { useState } from 'react'
import { useParams } from 'react-router'
import { toast } from 'sonner'
import { Badge, Button, Skeleton } from '@/ui'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchMission } from '@/api/missions'
import { fetchScenario } from '@/api/scenarios'
import { fetchCurrentContract } from '@/api/contract'
import {
  fetchActionPlans,
  generateActionPlan,
  validateActionPlan,
  approveActionPlan,
  ACTION_PLAN_STATUS_LABELS,
  type ActionPlanVersion,
  type CommandIR,
  type ValidateActionPlanResult,
} from '@/api/actionPlans'
import { ActionPlanEditor } from '@/components/browser/ActionPlanEditor'
import { CommandDiff } from '@/components/browser/CommandDiff'
import { Sparkles, Check, ShieldCheck, GitCompare } from '@/lib/icons'

/** @/missions/:missionId/scenarios/:scenarioId/action-plan */
export default function MissionActionPlanPage() {
  const { missionId, scenarioId } = useParams()
  const missionIdNum = Number(missionId)
  const scenarioIdNum = Number(scenarioId)
  useDocumentTitle('Action Plan')

  const [scenarioVersionId, setScenarioVersionId] = useState<number | null>(null)
  const [contractVersionId, setContractVersionId] = useState<number | null>(null)
  const [versions, setVersions] = useState<ActionPlanVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [currentIr, setCurrentIr] = useState<CommandIR>({ schema_version: '1.0', commands: [] })
  const [generating, setGenerating] = useState(false)
  const [validation, setValidation] = useState<Record<number, ValidateActionPlanResult | null>>({})
  const [baselineId, setBaselineId] = useState<number | null>(null)
  const [candidateId, setCandidateId] = useState<number | null>(null)

  const reloadVersions = async () => {
    try {
      setVersions(await fetchActionPlans(scenarioIdNum))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载 Action Plan 失败')
    }
  }

  useAbortableEffect((signal) => {
    if (!missionIdNum || !scenarioIdNum) return
    setLoading(true)
    Promise.all([
      fetchMission(missionIdNum, signal),
      fetchScenario(scenarioIdNum),
      fetchCurrentContract(missionIdNum),
      fetchActionPlans(scenarioIdNum, signal),
    ])
      .then(([mission, scenario, contract, planVersions]) => {
        setScenarioVersionId(scenario.scenario_version_id)
        setContractVersionId(contract?.version?.id ?? mission.current_contract_version_id)
        setVersions(planVersions)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载 Action Plan 失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionIdNum, scenarioIdNum])

  const doGenerate = async () => {
    if (!scenarioVersionId) {
      toast.error('场景版本缺失')
      return
    }
    if (!contractVersionId) {
      toast.error('契约版本缺失，无法生成 Action Plan')
      return
    }
    setGenerating(true)
    try {
      const version = await generateActionPlan(scenarioIdNum, {
        scenario_version_id: scenarioVersionId,
        contract_version_id: contractVersionId,
        plan: currentIr,
      })
      toast.success(`Action Plan 版本 #${version.version_no} 已生成`)
      setCurrentIr(version.plan_json ?? currentIr)
      await reloadVersions()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const doValidate = async (versionId: number) => {
    try {
      const result = await validateActionPlan(versionId)
      setValidation((prev) => ({ ...prev, [versionId]: result }))
      toast.success(result.valid ? '校验通过' : '校验未通过')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '校验失败')
    }
  }

  const doApprove = async (versionId: number) => {
    try {
      await approveActionPlan(versionId)
      toast.success('已批准 Action Plan')
      await reloadVersions()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '批准失败')
    }
  }

  const baseline = versions.find((v) => v.id === baselineId) ?? null
  const candidate = versions.find((v) => v.id === candidateId) ?? null

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-xl font-semibold tracking-[-0.02em]">Command IR 编辑器</h2>
            <p className="text-sm text-muted-foreground">
              编辑命令后生成 Action Plan。驱动：browser / data / api / assertion。
            </p>
          </div>
          <Button onClick={doGenerate} disabled={generating || !scenarioVersionId || !contractVersionId}>
            <Sparkles className="size-4" /> {generating ? '生成中…' : '生成 Action Plan'}
          </Button>
        </div>
        <ActionPlanEditor value={currentIr} onChange={setCurrentIr} />
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold tracking-[-0.02em]">版本列表</h2>
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>版本</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>schema</TableHead>
                <TableHead>生成方式</TableHead>
                <TableHead>model</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {versions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                    尚未生成 Action Plan。编辑上方命令后点击「生成」。
                  </TableCell>
                </TableRow>
              ) : (
                versions.map((v) => {
                  const statusMeta = ACTION_PLAN_STATUS_LABELS[v.status]
                  const validateResult = validation[v.id]
                  return (
                    <TableRow key={v.id}>
                      <TableCell>
                        <p className="font-mono text-xs">#{v.version_no}</p>
                        <p className="text-xs text-muted-foreground">{v.plan_hash.slice(0, 12)}…</p>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={statusMeta?.color}>
                          {statusMeta?.label ?? v.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{v.schema_version}</TableCell>
                      <TableCell className="text-xs">{v.generated_by_type}</TableCell>
                      <TableCell className="text-xs">{v.model_ref ?? '—'}</TableCell>
                      <TableCell className="font-mono text-xs">{v.created_at ?? '—'}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => doValidate(v.id)}>
                            <ShieldCheck className="size-3.5" /> 校验
                          </Button>
                          {v.status !== 'APPROVED' && (
                            <Button variant="ghost" size="sm" onClick={() => doApprove(v.id)}>
                              <Check className="size-3.5" /> 批准
                            </Button>
                          )}
                        </div>
                        {validateResult && (
                          <div className="mt-1 text-right">
                            {validateResult.valid ? (
                              <span className="text-xs text-status-success">有效</span>
                            ) : (
                              <span className="text-xs text-status-danger">无效 · {validateResult.errors.length} 错误</span>
                            )}
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold tracking-[-0.02em]">
          <GitCompare className="size-4" /> 版本对比
        </h2>
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">基准版本</span>
            <Select value={baselineId === null ? '' : String(baselineId)} onValueChange={(v) => setBaselineId(v ? Number(v) : null)}>
              <SelectTrigger>
                <SelectValue placeholder="选择基准" />
              </SelectTrigger>
              <SelectContent>
                {versions.map((v) => (
                  <SelectItem key={v.id} value={String(v.id)}>#{v.version_no} · {v.status}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">候选版本</span>
            <Select value={candidateId === null ? '' : String(candidateId)} onValueChange={(v) => setCandidateId(v ? Number(v) : null)}>
              <SelectTrigger>
                <SelectValue placeholder="选择候选" />
              </SelectTrigger>
              <SelectContent>
                {versions.map((v) => (
                  <SelectItem key={v.id} value={String(v.id)}>#{v.version_no} · {v.status}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <CommandDiff before={baseline?.plan_json ?? null} after={candidate?.plan_json ?? null} />
      </section>
    </div>
  )
}
