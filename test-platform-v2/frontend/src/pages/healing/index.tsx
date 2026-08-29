import { useState } from 'react'
import { Button, Input, Skeleton } from '@/ui'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from 'sonner'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchActionPlans,
  ACTION_PLAN_STATUS_LABELS,
  type ActionPlanVersion,
} from '@/api/actionPlans'
import { HealingProposalDiff } from '@/components/browser/HealingProposalDiff'
import { OracleChangeGuardBadge } from '@/components/browser/OracleChangeGuardBadge'
import { collectOracleKeys } from '@/components/browser/CommandDiff'

function sameOracleKeys(before: string[], after: string[]): boolean {
  if (before.length !== after.length) return false
  return before.every((k, i) => k === after[i])
}

/** Standalone healing-review panel: compare two Action Plan revisions /after. */
export default function HealingReviewPage() {
  useDocumentTitle('愈合评审')

  const [scenarioInput, setScenarioInput] = useState('')
  const [scenarioId, setScenarioId] = useState<number | null>(null)
  const [versions, setVersions] = useState<ActionPlanVersion[]>([])
  const [loading, setLoading] = useState(false)
  const [baselineId, setBaselineId] = useState<number | null>(null)
  const [candidateId, setCandidateId] = useState<number | null>(null)

  useAbortableEffect((signal) => {
    if (!scenarioId) return
    setLoading(true)
    fetchActionPlans(scenarioId)
      .then((rows) => {
        setVersions(rows)
        setBaselineId(rows[0]?.id ?? null)
        setCandidateId(rows[rows.length - 1]?.id ?? null)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载 Action Plan 失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [scenarioId])

  const doLoad = () => {
    const sid = Number(scenarioInput)
    if (!sid) {
      toast.error('请输入 scenario_id')
      return
    }
    setScenarioId(sid)
  }

  const baseline = versions.find((v) => v.id === baselineId) ?? null
  const candidate = versions.find((v) => v.id === candidateId) ?? null
  const oracleChanged =
    baseline && candidate
      ? !sameOracleKeys(collectOracleKeys(baseline.plan_json), collectOracleKeys(candidate.plan_json))
      : false

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold tracking-[-0.02em]">愈合评审 (Healing Review)</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          对比基准与候选 Action Plan 的 Command IR，并显示 Oracle 变更守卫。愈合提案中的
          Oracle 变更必须显式暴露给评审人。
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-2">
        <div className="w-48 space-y-1.5">
          <label htmlFor="healing-scenario" className="text-xs font-medium text-muted-foreground">scenario_id</label>
          <Input
            id="healing-scenario"
            type="number"
            value={scenarioInput}
            onChange={(e) => setScenarioInput(e.target.value)}
            placeholder="场景 ID"
          />
        </div>
        <Button onClick={doLoad} disabled={loading}>
          {loading ? '加载中…' : '加载版本'}
        </Button>
        <span className="text-xs text-muted-foreground">
          {versions.length > 0 ? `共 ${versions.length} 个版本` : '尚未加载'}
        </span>
      </div>

      {(loading || !scenarioId) ? (
        loading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : (
          <div className="rounded-md border border-dashed px-3 py-10 text-center text-sm text-muted-foreground">
            <OracleChangeGuardBadge changed={false} detail="占位：输入 scenario_id 以加载版本进行前后对比。" />
          </div>
        )
      ) : (
        <>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground">基准版本</span>
              <Select value={baselineId === null ? '' : String(baselineId)} onValueChange={(v) => setBaselineId(v ? Number(v) : null)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择基准" />
                </SelectTrigger>
                <SelectContent>
                  {versions.map((v) => (
                    <SelectItem key={v.id} value={String(v.id)}>
                      #{v.version_no} · {ACTION_PLAN_STATUS_LABELS[v.status]?.label ?? v.status}
                    </SelectItem>
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
                    <SelectItem key={v.id} value={String(v.id)}>
                      #{v.version_no} · {ACTION_PLAN_STATUS_LABELS[v.status]?.label ?? v.status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <HealingProposalDiff
            before={baseline?.plan_json ?? null}
            after={candidate?.plan_json ?? null}
            oracleChanged={oracleChanged}
          />
        </>
      )}
    </div>
  )
}
