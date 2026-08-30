import { useState } from 'react'
import { Badge, Skeleton } from '@/ui'
import PageHeader from '@/components/PageHeader'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchJourneys, type Journey } from '@/api/production'
import { ProdReadOnlyBanner } from './components/ProdReadOnlyBanner'
import { ObservedJourneyTimeline } from './components/ObservedJourneyTimeline'
import { Layers } from '@/lib/icons'

/**
 * /production/journeys — observed journeys list + expandable step timelines
 * with sanitized XHR evidence.
 */
export default function ProductionJourneysPage() {
  const [journeys, setJourneys] = useState<Journey[]>([])
  const [loading, setLoading] = useState(true)

  useAbortableEffect((signal) => {
    setLoading(true)
    fetchJourneys(undefined, signal)
      .then((rows) => {
        if (!signal.aborted) setJourneys(rows)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) return
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [])

  return (
    <div className="space-y-4">
      <ProdReadOnlyBanner />
      <PageHeader
        title="Journeys"
        description="观察到的真实世界 Journey 回放与脱敏网络证据（V36-013/014）"
      />
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Layers className="size-4" />
        <span>全部 Journey</span>
        {!loading && <Badge tone="neutral">{journeys.length}</Badge>}
      </div>
      {loading ? (
        <Skeleton className="h-32 w-full" />
      ) : (
        <ObservedJourneyTimeline journeys={journeys} loading={loading} />
      )}
    </div>
  )
}
