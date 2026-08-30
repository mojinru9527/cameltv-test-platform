import { useParams } from 'react-router'
import { useState } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { backfillLineage, fetchLineage, type LineageEdge } from '@/api/smartRegression'

/** V37-001/002 + V37-014 Lineage view: source → ... → run navigation. */
export default function MissionTracePage() {
  const { id } = useParams()
  const missionId = Number(id)
  useDocumentTitle('Lineage')
  const [edges, setEdges] = useState<LineageEdge[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const load = (signal?: AbortSignal) => {
    if (!missionId) return
    setLoading(true)
    fetchLineage(missionId, signal)
      .then((r) => setEdges(r.edges))
      .catch(() => undefined)
      .finally(() => {
        if (!signal?.aborted) setLoading(false)
      })
  }

  useAbortableEffect((signal) => {
    load(signal)
  }, [missionId])

  const onBackfill = async () => {
    setBusy(true)
    try {
      const r = await backfillLineage(missionId)
      setEdges((prev) => prev)
      void load()
      void r
    } finally {
      setBusy(false)
    }
  }

  if (loading && !edges.length) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader title="Lineage" description="Source → Scope → Contract → Scenario → Oracle → Run 可追溯（V37-014）" />
      <div className="flex items-center gap-2">
        <Button size="sm" onClick={onBackfill} disabled={busy}>
          {busy ? '回填中…' : `回填 V3.0-V3.6 Lineage（${edges.length} 边）`}
        </Button>
      </div>
      {edges.length === 0 ? (
        <p className="text-sm text-muted-foreground">暂无 Lineage 边。点击「回填」生成。</p>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Lineage 边（{edges.length}）</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {edges.map((e) => (
              <div key={e.id} className="flex flex-wrap items-center gap-2 border-b py-1.5 text-sm last:border-0">
                <span className="font-mono text-xs text-muted-foreground">{e.from}</span>
                <Badge tone="neutral">{e.edge_type}</Badge>
                <span className="font-mono text-xs text-muted-foreground">{e.to}</span>
                {e.confidence < 1 && <Badge tone="warning">conf {e.confidence}</Badge>}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
