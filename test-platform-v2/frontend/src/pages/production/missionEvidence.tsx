import { useState } from 'react'
import { useParams } from 'react-router'
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle, Skeleton } from '@/ui'
import PageHeader from '@/components/PageHeader'
import { useAuthStore } from '@/stores/auth'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchMission } from '@/api/missions'
import {
  fetchJourneys,
  type Journey,
  type JourneyDetail,
  type JourneyStep,
  type ObservationSession,
} from '@/api/production'
import { ProdReadOnlyBanner } from './components/ProdReadOnlyBanner'
import { ObservationSessionPanel } from './components/ObservationSessionPanel'
import { ObservedJourneyTimeline } from './components/ObservedJourneyTimeline'
import { RealStateDiscoveryTable } from './components/RealStateDiscoveryTable'
import { Layers } from '@/lib/icons'

/**
 * /missions/:id/production-evidence — mission-scoped production evidence.
 */
export default function MissionProductionEvidencePage() {
  const { id } = useParams()
  const missionId = Number(id)
  const currentProjectId = useAuthStore((s) => s.currentProjectId)
  const [missionLoading, setMissionLoading] = useState(true)
  const [projectId, setProjectId] = useState<number | null>(currentProjectId)
  const [environmentId, setEnvironmentId] = useState<number | null>(null)
  const [session, setSession] = useState<ObservationSession | null>(null)
  const [journeys, setJourneys] = useState<Journey[]>([])
  const [journeysLoading, setJourneysLoading] = useState(false)
  const [stepsByJourney, setStepsByJourney] = useState<Record<number, JourneyStep[]>>({})

  useAbortableEffect((signal) => {
    if (!Number.isFinite(missionId) || missionId <= 0) return
    setMissionLoading(true)
    fetchMission(missionId, signal)
      .then((mission) => {
        if (signal.aborted) return
        setProjectId(mission.project_id)
        setEnvironmentId(mission.default_environment_id)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) return
      })
      .finally(() => {
        if (!signal.aborted) setMissionLoading(false)
      })
  }, [missionId])

  useAbortableEffect((signal) => {
    const sessionId = session?.id
    setJourneysLoading(true)
    setJourneys([])
    setStepsByJourney({})
    fetchJourneys(sessionId, signal)
      .then((rows) => {
        if (!signal.aborted) setJourneys(rows)
      })
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) return
      })
      .finally(() => {
        if (!signal.aborted) setJourneysLoading(false)
      })
  }, [session?.id])

  const handleJourneyDetail = (detail: JourneyDetail) => {
    setStepsByJourney((prev) => ({ ...prev, [detail.id]: detail.steps }))
  }

  if (missionLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <ProdReadOnlyBanner />
      <PageHeader
        title="生产证据"
        description={`Mission #${missionId} 的真实世界数据证据（V36-013/014）`}
      />
      <ObservationSessionPanel
        projectId={projectId}
        environmentId={environmentId}
        missionId={missionId}
        defaultMode="OBSERVE"
        onChange={(next) => setSession(next)}
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers className="size-4" /> 真实状态发现
            <Badge tone="neutral">{journeys.length} Journeys</Badge>
          </CardTitle>
          <CardDescription>
            {session ? `会话 #${session.id} 期间的 Journey 与步骤证据。` : '启动观察会话后将在这里展示 Journey。'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ObservedJourneyTimeline
            journeys={journeys}
            loading={journeysLoading}
            onDetail={handleJourneyDetail}
          />
          <RealStateDiscoveryTable journeys={journeys} loading={journeysLoading} stepsByJourney={stepsByJourney} />
        </CardContent>
      </Card>
    </div>
  )
}
