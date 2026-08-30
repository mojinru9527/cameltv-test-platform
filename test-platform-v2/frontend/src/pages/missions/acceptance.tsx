import { useParams, Link } from 'react-router'
import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
} from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchMissionAcceptance,
  fetchMissionBuilds,
  fetchMissionCampaigns,
  evaluateGate,
  GATE_RESULT_LABELS,
  type BuildObservation,
  type Campaign,
  type GateResult,
} from '@/api/continuous'

interface GateCheck {
  gate: string
  label?: string
  pass: boolean
  detail: string
}

/** Parse the backend checks_json (string or already-parsed list). */
function parseChecks(value: GateResult['checks_json']): GateCheck[] {
  if (Array.isArray(value)) return value as unknown as GateCheck[]
  if (typeof value === 'string') {
    try {
      return JSON.parse(value) as GateCheck[]
    } catch {
      return []
    }
  }
  return []
}

/** V35-012 Acceptance Dashboard — Quality Gate RED→GREEN + override audit. */
export default function MissionAcceptancePage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('验收')
  const [results, setResults] = useState<GateResult[]>([])
  const [builds, setBuilds] = useState<BuildObservation[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [selectedBuild, setSelectedBuild] = useState<string>('')
  const [selectedCampaign, setSelectedCampaign] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [evaluating, setEvaluating] = useState(false)

  const load = (signal?: AbortSignal) => {
    setLoading(true)
    return Promise.all([
      fetchMissionAcceptance(missionId, signal),
      fetchMissionBuilds(missionId, signal),
      fetchMissionCampaigns(missionId, signal),
    ])
      .then(([acc, bld, cmp]) => {
        setResults(acc.items)
        setBuilds(bld.items)
        setCampaigns(cmp.items)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) return
      })
      .finally(() => {
        if (!signal?.aborted) setLoading(false)
      })
  }

  useAbortableEffect((signal) => {
    if (!missionId) return
    load(signal)
  }, [missionId])

  const onEvaluate = async () => {
    setEvaluating(true)
    try {
      await evaluateGate(missionId, {
        campaign_id: selectedCampaign ? Number(selectedCampaign) : null,
        build_observation_id: selectedBuild ? Number(selectedBuild) : null,
      })
      load()
    } finally {
      setEvaluating(false)
    }
  }

  if (loading && !results.length) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="验收"
        description="Quality Gate 对当前 Build 的 RED→GREEN 判定（V35-012）"
      />
      <div className="flex flex-wrap items-center gap-2">
        <Select value={selectedBuild} onValueChange={setSelectedBuild}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="选择 Build" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部 Build</SelectItem>
            {builds.map((b) => (
              <SelectItem key={b.id} value={String(b.id)}>
                Build #{b.id} · fp {b.fingerprint_id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={selectedCampaign} onValueChange={setSelectedCampaign}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="选择 Campaign" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部 Campaign</SelectItem>
            {campaigns.map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>
                {c.name || `Campaign #${c.id}`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button size="sm" onClick={onEvaluate} disabled={evaluating}>
          {evaluating ? '评估中…' : '评估 Gate'}
        </Button>
      </div>
      {results.length === 0 ? (
        <p className="text-sm text-muted-foreground">暂无验收结果。选择 Build/Campaign 后点击「评估 Gate」生成。</p>
      ) : (
        <div className="space-y-3">
          {results.map((r) => {
            const meta = GATE_RESULT_LABELS[r.result]
            const checks = parseChecks(r.checks_json)
            const passed = checks.filter((c) => c.pass).length
            return (
              <Card key={r.id}>
                <CardHeader>
                  <CardTitle className="flex flex-wrap items-center gap-2">
                    结果
                    <Badge tone="neutral" className={meta?.color}>{meta?.label ?? r.result}</Badge>
                    {r.campaign_id && (
                      <Link to={`/campaigns/${r.campaign_id}`} className="text-xs text-muted-foreground hover:underline">
                        查看 Campaign #{r.campaign_id} →
                      </Link>
                    )}
                    {r.override_status && <Badge tone="warning">已覆盖: {r.override_status}</Badge>}
                  </CardTitle>
                  <div className="text-xs text-muted-foreground">
                    评估时间：{r.evaluated_at ? new Date(r.evaluated_at).toLocaleString() : '-'}
                    {' · '}Gate 通过 {passed}/{checks.length}
                    {r.build_observation_id && <> · Build #{r.build_observation_id}</>}
                  </div>
                </CardHeader>
                <CardContent className="space-y-1.5">
                  {checks.length ? (
                    checks.map((c) => (
                      <div key={c.gate} className="flex items-start justify-between gap-2 text-sm">
                        <div className="flex items-center gap-2">
                          <Badge tone="neutral" className={c.pass ? 'bg-status-success-muted text-status-success' : 'bg-status-danger-muted text-status-danger'}>
                            {c.pass ? 'PASS' : 'FAIL'}
                          </Badge>
                          <span className="font-mono text-xs">{c.gate}</span>
                          <span className="font-medium">{c.label ?? ''}</span>
                        </div>
                        <span className="max-w-[46ch] text-right text-xs text-muted-foreground">{c.detail}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-muted-foreground">无 Gate 明细。</div>
                  )}
                  {r.override_reason && (
                    <div className="mt-2 text-sm">覆盖理由（审计）：{r.override_reason}</div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
