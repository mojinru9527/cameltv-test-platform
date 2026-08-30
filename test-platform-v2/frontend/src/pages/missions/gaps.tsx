import { useParams } from 'react-router'
import { useState } from 'react'
import { Badge, Button, Skeleton } from '@/ui'
import { toast } from 'sonner'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  convertScenarioGap,
  listScenarioGaps,
  GAP_TYPE_LABELS,
  type ScenarioGap,
} from '@/api/aiClosedLoop'

/** V38-010 Mission Scenario Gaps: proposal-only detected gaps for a Mission. */
export default function MissionGapsPage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('场景缺口')
  const [gaps, setGaps] = useState<ScenarioGap[]>([])
  const [loading, setLoading] = useState(false)
  const [convertingId, setConvertingId] = useState<number | null>(null)

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    listScenarioGaps(missionId, signal)
      .then((rows) => setGaps(rows))
      .catch(() => undefined)
      .finally(() => {
        if (!signal?.aborted) setLoading(false)
      })
  }, [missionId])

  const convert = async (gap: ScenarioGap) => {
    if (convertingId !== null) return
    setConvertingId(gap.id)
    try {
      const res = await convertScenarioGap(gap.id, { title: gap.title, risk_level: gap.risk_level })
      toast.success(`已转 Proposal：${res.title}`)
      setGaps((rows) => rows.map((g) => (g.id === gap.id ? { ...g, status: 'CONVERTED' } : g)))
    } catch (err) {
      toast.error((err as Error).message || '转换失败')
    } finally {
      setConvertingId(null)
    }
  }

  if (loading && gaps.length === 0) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader title="场景缺口" description={`Mission #${missionId} 的 Gap Candidates（V38-010，proposal only）`} />
      {gaps.length === 0 ? (
        <div className="rounded-md border border-dashed px-3 py-10 text-center text-sm text-muted-foreground">
          暂无 Gap 候选
        </div>
      ) : (
        <div className="space-y-2">
          {gaps.map((g) => (
            <div key={g.id} className="rounded-md border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="neutral">{GAP_TYPE_LABELS[g.gap_type] ?? g.gap_type}</Badge>
                <Badge tone="neutral">{g.risk_level}</Badge>
                <Badge tone="neutral">{g.status}</Badge>
                <span className="text-xs text-muted-foreground">置信度 {(g.confidence * 100).toFixed(0)}%</span>
              </div>
              <p className="mt-2 text-sm font-medium">{g.title}</p>
              {g.description && <p className="mt-1 text-sm text-muted-foreground">{g.description}</p>}
              {g.status === 'OPEN' && (
                <Button
                  size="sm"
                  className="mt-2"
                  onClick={() => convert(g)}
                  disabled={convertingId !== null}
                >
                  {convertingId === g.id ? '转换中…' : '转 Contract/Scenario Proposal'}
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
