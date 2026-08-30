import { useParams, useSearchParams, Link } from 'react-router'
import { useState } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  analyzeImpact,
  createCampaignFromSelection,
  createSelection,
  guardSelection,
  RISK_LABELS,
  type ImpactRun,
  type RegressionSelection,
} from '@/api/smartRegression'

/** V37-008..011 Impact analysis → regression selection → coverage guard → campaign. */
export default function MissionImpactPage() {
  const { id } = useParams()
  const missionId = Number(id)
  const [searchParams] = useSearchParams()
  const changeSetId = Number(searchParams.get('changeSet') ?? 0)
  useDocumentTitle('影响分析')
  const [run, setRun] = useState<ImpactRun | null>(null)
  const [selection, setSelection] = useState<RegressionSelection | null>(null)
  const [guard, setGuard] = useState<{ ok: boolean; fallback_to?: string | null; fallback_reason?: string | null } | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)

  useAbortableEffect((signal) => {
    if (!missionId || !changeSetId) return
    setLoading(true)
    analyzeImpact(changeSetId)
      .then((r) => setRun(r))
      .catch(() => undefined)
      .finally(() => {
        if (!signal?.aborted) setLoading(false)
      })
  }, [missionId, changeSetId])

  const onSelect = async () => {
    if (!run) return
    setBusy(true)
    try {
      const sel = await createSelection(run.id, { selection_type: 'SMART' })
      setSelection(sel)
      const g = await guardSelection(sel.id)
      setGuard(g)
    } finally {
      setBusy(false)
    }
  }

  const onCampaign = async () => {
    if (!selection) return
    setBusy(true)
    try {
      await createCampaignFromSelection(selection.id, { name: 'Smart Regression', environment_id: 0 })
      setGuard({ ok: true })
    } finally {
      setBusy(false)
    }
  }

  if (!changeSetId) {
    return (
      <div className="space-y-4">
        <PageHeader title="影响分析" description="针对 ChangeSet 的影响分析 / 回归选择（V37-008..011）" />
        <p className="text-sm text-muted-foreground">
          请先在「变化检测」页检测 ChangeSet，然后在 URL 追加 <code className="font-mono">?changeSet=&lt;id&gt;</code> 进入影响分析。
        </p>
      </div>
    )
  }

  if (loading && !run) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader title="影响分析" description={`ChangeSet #${changeSetId} 的 Impact Run（V37-008）`} />
      {run ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center gap-2">
              Impact Run #{run.id}
              <Badge tone="neutral">{run.algorithm_version}</Badge>
              <Badge tone="neutral">{run.status}</Badge>
            </CardTitle>
            <div className="text-xs text-muted-foreground">
              受影响 Scenario {run.results.length} 个 · 未知变化 {run.unknown_changes.length} 个 · 结束 {run.finished_at ? new Date(run.finished_at).toLocaleString() : '-'}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={onSelect} disabled={busy}>
                {busy ? '处理中…' : '生成 SMART 回归选择'}
              </Button>
              {selection && (
                <Button size="sm" variant="secondary" onClick={onCampaign} disabled={busy}>
                  固化为 Campaign
                </Button>
              )}
            </div>

            {run.results.length === 0 ? (
              <p className="text-sm text-muted-foreground">无受影响 Scenario。</p>
            ) : (
              <div className="space-y-1.5">
                {run.results.map((r) => {
                  const meta = RISK_LABELS[r.risk_level]
                  return (
                    <div key={r.id} className="flex flex-wrap items-center gap-2 rounded-md border p-2 text-sm">
                      <Badge tone="neutral" className={meta?.color ?? ''}>{r.risk_level}</Badge>
                      <span className="font-medium">Scenario #{r.scenario_id}</span>
                      <span className="text-xs text-muted-foreground">版本 #{r.scenario_version_id || '—'}</span>
                      <span className="text-xs text-muted-foreground">score {r.impact_score.toFixed(2)}</span>
                      {r.paths.length > 0 && (
                        <Link to={`?changeSet=${changeSetId}&scenario=${r.scenario_id}`} className="ml-auto text-xs text-muted-foreground hover:underline">
                          {r.reasons.length} 条原因 →
                        </Link>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {guard && (
              <div className={`rounded-md border p-3 text-sm ${guard.ok ? 'border-status-success text-status-success' : 'border-status-warning text-status-warning'}`}>
                {guard.ok ? 'Coverage Guard 通过，无需 fallback。' : `Coverage Guard 触发 fallback → ${guard.fallback_to}: ${guard.fallback_reason ?? ''}`}
              </div>
            )}

            {selection && (
              <div className="space-y-1.5">
                <div className="text-sm font-medium">回归选择 #{selection.id}（{selection.selection_type}）</div>
                <div className="flex flex-wrap gap-1.5">
                  {selection.selected.map((s) => (
                    <Badge key={s.scenario_id} tone="neutral">选中 S#{s.scenario_id}</Badge>
                  ))}
                  {selection.excluded.map((s) => (
                    <Badge key={s.scenario_id} tone="neutral" className="bg-muted text-muted-foreground">排除 S#{s.scenario_id}</Badge>
                  ))}
                </div>
                <Link to={`/regression-selections/${selection.id}`} className="text-xs text-muted-foreground hover:underline">
                  打开选择详情 →
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <p className="text-sm text-muted-foreground">Impact Run 不存在。</p>
      )}
    </div>
  )
}
