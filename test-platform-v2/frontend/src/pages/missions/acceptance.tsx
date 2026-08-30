import { useParams } from 'react-router'
import { useState } from 'react'
import { Badge, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { Button } from '@/ui'
import {
  fetchMissionAcceptance,
  evaluateGate,
  GATE_RESULT_LABELS,
  type GateResult,
} from '@/api/continuous'

/** V35-012 Acceptance Dashboard — Quality Gate RED→GREEN + override audit. */
export default function MissionAcceptancePage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('验收')
  const [results, setResults] = useState<GateResult[]>([])
  const [loading, setLoading] = useState(true)

  const load = (signal?: AbortSignal) => {
    setLoading(true)
    return fetchMissionAcceptance(missionId, signal)
      .then((res) => setResults(res.items))
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
    await evaluateGate(missionId, {})
    load()
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
      <Button size="sm" onClick={onEvaluate}>评估 Gate</Button>
      {results.length === 0 ? (
        <p className="text-sm text-muted-foreground">暂无验收结果。点击「评估 Gate」生成。</p>
      ) : (
        <div className="space-y-3">
          {results.map((r) => {
            const meta = GATE_RESULT_LABELS[r.result]
            return (
              <Card key={r.id}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    结果
                    <Badge tone="neutral" className={meta?.color}>{meta?.label ?? r.result}</Badge>
                    {r.override_status && <Badge tone="warning">已覆盖: {r.override_status}</Badge>}
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  <div>评估时间：{r.evaluated_at ? new Date(r.evaluated_at).toLocaleString() : '-'}</div>
                  <div className="mt-2">checks 见 payload（GA 引擎 G1-G10）。</div>
                  {r.override_reason && (
                    <div className="mt-2">覆盖理由（审计）：{r.override_reason}</div>
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
