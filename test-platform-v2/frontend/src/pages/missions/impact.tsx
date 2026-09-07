import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { toast } from 'sonner'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  analyzeImpact,
  createCampaignFromSelection,
  createSelection,
  fetchMissionImpactRuns,
  guardSelection,
  IMPACT_STATUS_LABELS,
  RISK_LABELS,
  SELECTION_TYPE_LABELS,
  type ImpactRun,
  type RegressionSelection,
} from '@/api/smartRegression'

export default function MissionImpactPage() {
  const { id } = useParams()
  const missionId = Number(id)
  const [searchParams] = useSearchParams()
  const requestedChangeSetId = Number(searchParams.get('changeSet') ?? 0)
  useDocumentTitle('影响分析')
  const [runs, setRuns] = useState<ImpactRun[]>([])
  const [run, setRun] = useState<ImpactRun | null>(null)
  const [selection, setSelection] = useState<RegressionSelection | null>(null)
  const [guard, setGuard] = useState<{
    ok: boolean
    fallback_to?: string | null
    fallback_reason?: string | null
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    fetchMissionImpactRuns(missionId, signal)
      .then(({ items }) => {
        setRuns(items)
        const selected = requestedChangeSetId
          ? items.find((item) => item.change_set_id === requestedChangeSetId) ?? null
          : items[0] ?? null
        setRun(selected)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '影响分析加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId, requestedChangeSetId])

  const onAnalyze = async () => {
    if (!requestedChangeSetId || busy) return
    setBusy(true)
    try {
      const created = await analyzeImpact(requestedChangeSetId)
      setRun(created)
      setRuns((items) => [created, ...items.filter((item) => item.id !== created.id)])
      toast.success('影响分析已完成')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '影响分析失败')
    } finally {
      setBusy(false)
    }
  }

  const onSelect = async () => {
    if (!run || busy) return
    setBusy(true)
    try {
      const selected = await createSelection(run.id, { selection_type: 'SMART' })
      setSelection(selected)
      setGuard(await guardSelection(selected.id))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '回归选择失败')
    } finally {
      setBusy(false)
    }
  }

  const onCampaign = async () => {
    if (!selection || busy) return
    setBusy(true)
    try {
      await createCampaignFromSelection(selection.id, {
        name: 'Smart Regression',
        environment_id: 0,
      })
      toast.success('Campaign 已创建')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Campaign 创建失败')
    } finally {
      setBusy(false)
    }
  }

  if (loading && runs.length === 0) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader title="影响分析" />

      {!run && requestedChangeSetId > 0 && (
        <div className="flex items-center justify-between gap-3 rounded-md border p-3">
          <span className="text-sm">变化记录 #{requestedChangeSetId} 尚未分析</span>
          <Button size="sm" disabled={busy} onClick={onAnalyze}>
            {busy ? '分析中…' : '开始分析'}
          </Button>
        </div>
      )}

      {run ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2 text-base">
              影响分析 #{run.id}
              <Badge tone="neutral">{run.algorithm_version}</Badge>
              <Badge tone="neutral">{IMPACT_STATUS_LABELS[run.status] ?? run.status}</Badge>
            </CardTitle>
            <div className="text-xs text-muted-foreground">
              变化记录 #{run.change_set_id} · 受影响场景 {run.results.length} 个 · 未知变化 {run.unknown_changes.length} 个
              {' · '}{run.finished_at ? new Date(run.finished_at).toLocaleString() : '-'}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={onSelect} disabled={busy}>
                {busy ? '处理中…' : '生成回归范围'}
              </Button>
              {selection && (
                <Button size="sm" variant="secondary" onClick={onCampaign} disabled={busy}>
                  创建 Campaign
                </Button>
              )}
            </div>

            {run.results.length === 0 ? (
              <p className="text-sm text-muted-foreground">本次分析未识别到受影响场景。</p>
            ) : (
              <div className="space-y-1.5">
                {run.results.map((result) => {
                  const meta = RISK_LABELS[result.risk_level]
                  return (
                    <div
                      key={result.id}
                      className="grid gap-1 rounded-md border p-2 text-sm sm:grid-cols-[auto_minmax(10rem,1fr)_auto] sm:items-center"
                    >
                      <Badge tone="neutral" className={meta?.color ?? ''}>
                        {meta?.label ?? result.risk_level}
                      </Badge>
                      <div>
                        <p className="font-medium">Scenario #{result.scenario_id}</p>
                        <p className="text-xs text-muted-foreground">
                          {result.reasons.join('；') || '无原因说明'}
                        </p>
                      </div>
                      <span className="text-xs text-muted-foreground">影响分 {result.impact_score.toFixed(2)}</span>
                    </div>
                  )
                })}
              </div>
            )}

            {guard && (
              <div className={`rounded-md border p-3 text-sm ${guard.ok ? 'border-status-success text-status-success' : 'border-status-warning text-status-warning'}`}>
                {guard.ok
                  ? 'Coverage Guard 通过。'
                  : `Coverage Guard 转为 ${guard.fallback_to}: ${guard.fallback_reason ?? ''}`}
              </div>
            )}

            {selection && (
              <div className="space-y-1.5">
                <div className="text-sm font-medium">
                  回归选择 #{selection.id}（{SELECTION_TYPE_LABELS[selection.selection_type] ?? selection.selection_type}）
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {selection.selected.map((item) => (
                    <Badge key={`selected-${item.scenario_id}`} tone="neutral">
                      选中 S#{item.scenario_id}
                    </Badge>
                  ))}
                  {selection.excluded.map((item) => (
                    <Badge key={`excluded-${item.scenario_id}`} tone="neutral" className="bg-muted text-muted-foreground">
                      排除 S#{item.scenario_id}
                    </Badge>
                  ))}
                </div>
                <Link to={`/regression-selections/${selection.id}`} className="text-xs text-muted-foreground hover:underline">
                  查看回归选择
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      ) : requestedChangeSetId === 0 ? (
        <div className="rounded-md border border-dashed px-3 py-10 text-center text-sm text-muted-foreground">
          尚无持久化的影响分析结果。
        </div>
      ) : null}
    </div>
  )
}
