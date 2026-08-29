import { useState } from 'react'
import { useParams } from 'react-router'
import { toast } from 'sonner'
import { Button, Skeleton, Card, CardHeader, CardTitle, CardContent } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchMissionScenarios, fetchScenario, type ScenarioRow } from '@/api/scenarios'
import {
  fetchDataRequirements,
  deriveDataRequirements,
  updateDataRequirement,
  type DataRequirement,
  type UpdateDataRequirementInput,
} from '@/api/dataRequirements'
import {
  createDataPlan,
  approveDataPlan,
  type DataPlan,
} from '@/api/dataPlans'
import { DataRequirementCard } from '@/components/data/DataRequirementCard'
import { DataPlanPreview } from '@/components/data/DataPlanPreview'

export default function MissionDataPage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('数据需求')

  const [rows, setRows] = useState<ScenarioRow[]>([])
  const [loading, setLoading] = useState(true)
  const [scenarioVersionId, setScenarioVersionId] = useState<number | null>(null)
  const [requirements, setRequirements] = useState<DataRequirement[]>([])
  const [deriving, setDeriving] = useState(false)
  const [saving, setSaving] = useState(false)
  const [plan, setPlan] = useState<DataPlan | null>(null)
  const [approving, setApproving] = useState(false)

  useAbortableEffect((signal) => {
    if (!missionId) return
    fetchMissionScenarios(missionId)
      .then(setRows)
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId])

  const selectScenario = async (scenarioId: number) => {
    setRequirements([])
    setPlan(null)
    try {
      const detail = await fetchScenario(scenarioId)
      const versionId = detail.scenario_version_id
      setScenarioVersionId(versionId)
      const reqs = await fetchDataRequirements(versionId)
      setRequirements(reqs)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加载数据需求失败')
    }
  }

  const doDerive = async () => {
    if (!scenarioVersionId || deriving) return
    setDeriving(true)
    try {
      const reqs = await deriveDataRequirements(scenarioVersionId)
      setRequirements(reqs)
      toast.success('已派生/刷新数据需求')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '派生失败')
    } finally {
      setDeriving(false)
    }
  }

  const doUpdate = async (requirementId: number, patch: UpdateDataRequirementInput) => {
    setSaving(true)
    try {
      await updateDataRequirement(requirementId, patch)
      toast.success('已更新数据需求')
      if (scenarioVersionId) setRequirements(await fetchDataRequirements(scenarioVersionId))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '更新失败')
    } finally {
      setSaving(false)
    }
  }

  const doGeneratePlan = async () => {
    if (!scenarioVersionId) return
    try {
      const p = await createDataPlan(scenarioVersionId, {})
      setPlan(p)
      toast.success('已生成数据计划')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成数据计划失败')
    }
  }

  const doApprovePlan = async () => {
    if (!plan) return
    setApproving(true)
    try {
      const p = await approveDataPlan(plan.id)
      setPlan(p)
      toast.success('已批准数据计划')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '批准失败')
    } finally {
      setApproving(false)
    }
  }

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
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold tracking-[-0.02em]">Data + DB Runtime</h2>
        <Button onClick={doDerive} disabled={!scenarioVersionId || deriving || loading}>
          {deriving ? '派生中…' : scenarioVersionId ? '派生候选需求' : '先选择场景'}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>选择场景</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {rows.map((row) => (
            <Button
              key={row.id}
              variant={scenarioVersionId === row.id ? 'primary' : 'secondary'}
              onClick={() => selectScenario(row.id)}
            >
              {row.scenario_key} · {row.title}
            </Button>
          ))}
          {rows.length === 0 && <p className="text-sm text-muted-foreground">该任务暂无场景。</p>}
        </CardContent>
      </Card>

      {scenarioVersionId && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>数据需求（业务描述，不生成 SQL）</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {requirements.length === 0 && (
                <p className="text-sm text-muted-foreground">暂无数据需求，点右上角「派生候选需求」。</p>
              )}
              {requirements.map((req) => (
                <DataRequirementCard
                  key={req.id}
                  requirement={req}
                  onUpdate={doUpdate}
                  saving={saving}
                />
              ))}
            </CardContent>
          </Card>

          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold tracking-[-0.02em]">数据计划</h3>
            <Button onClick={doGeneratePlan}>生成数据计划</Button>
          </div>
          {plan ? (
            <DataPlanPreview plan={plan} onApprove={doApprovePlan} approving={approving} />
          ) : (
            <p className="text-sm text-muted-foreground">尚未生成数据计划。</p>
          )}
        </>
      )}
    </div>
  )
}
