import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { toast } from 'sonner'
import { Badge, Button, Skeleton } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchMission } from '@/api/missions'
import { fetchScenario } from '@/api/scenarios'
import {
  deriveActionPlanFromSession,
  fetchBrowserSessionEvents,
  type BrowserSession,
  type BrowserSessionEvent,
} from '@/api/browserInteractions'
import type { CommandIR } from '@/api/actionPlans'
import { BrowserSessionPanel } from '@/components/browser/BrowserSessionPanel'
import { ObservationTimeline } from '@/components/browser/ObservationTimeline'
import { CapturedXhrPanel } from '@/components/browser/CapturedXhrPanel'
import { BrowserEvidencePanel } from '@/components/browser/BrowserEvidencePanel'
import { CommandDiff } from '@/components/browser/CommandDiff'
import { Sparkles, RefreshCw, BrainCircuit } from '@/lib/icons'

/** @/missions/:missionId/scenarios/:scenarioId/observe */
export default function ObservatePage() {
  const { missionId, scenarioId } = useParams()
  const missionIdNum = Number(missionId)
  const scenarioIdNum = Number(scenarioId)
  useDocumentTitle('观察 (Observe)')

  const [environmentId, setEnvironmentId] = useState<number | null>(null)
  const [session, setSession] = useState<BrowserSession | null>(null)
  const [events, setEvents] = useState<BrowserSessionEvent[]>([])
  const [eventsLoading, setEventsLoading] = useState(false)
  const [refreshTick, setRefreshTick] = useState(0)
  const [deriving, setDeriving] = useState(false)
  const [derivedPlan, setDerivedPlan] = useState<CommandIR | null>(null)
  const [loading, setLoading] = useState(true)

  useAbortableEffect((signal) => {
    if (!missionIdNum || !scenarioIdNum) return
    setLoading(true)
    Promise.all([fetchMission(missionIdNum, signal), fetchScenario(scenarioIdNum)])
      .then(([mission]) => setEnvironmentId(mission.default_environment_id))
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载上下文失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionIdNum, scenarioIdNum])

  useEffect(() => {
    if (!session) {
      setEvents([])
      return
    }
    let cancelled = false
    const load = () => {
      if (cancelled) return
      setEventsLoading(true)
      fetchBrowserSessionEvents(session.id)
        .then((rows) => {
          if (!cancelled) setEvents(rows)
        })
        .catch((err) => {
          if (!cancelled && err?.code !== 'ERR_CANCELED') toast.error(err.message || '加载事件失败')
        })
        .finally(() => {
          if (!cancelled) setEventsLoading(false)
        })
    }
    load()
    const timer = session.status === 'ACTIVE' ? window.setInterval(load, 4000) : null
    return () => {
      cancelled = true
      if (timer) window.clearInterval(timer)
    }
  }, [session, refreshTick])

  const doDerive = async () => {
    if (!session) return
    setDeriving(true)
    try {
      const plan = await deriveActionPlanFromSession(session.id)
      setDerivedPlan(plan)
      toast.success('已派生 Action Plan')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '派生失败')
    } finally {
      setDeriving(false)
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
    <div className="space-y-4">
      <BrowserSessionPanel
        missionId={missionIdNum}
        environmentId={environmentId}
        mode="OBSERVE"
        onSession={setSession}
      />

      {session && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold tracking-[-0.02em]">观察事件</h2>
            <Badge variant="outline">{events.length} 条</Badge>
            <Button variant="ghost" size="sm" onClick={() => setRefreshTick((t) => t + 1)}>
              <RefreshCw className="size-3.5" /> 刷新事件
            </Button>
          </div>

          <BrowserEvidencePanel events={events} />
          <ObservationTimeline events={events} loading={eventsLoading} />
          <CapturedXhrPanel events={events} />

          <div className="rounded-md border px-3 py-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm">
                <BrainCircuit className="size-4 text-muted-foreground" />
                <span className="text-muted-foreground">根据观察事件派生 Command IR。</span>
              </div>
              <Button variant="secondary" onClick={doDerive} disabled={deriving || session.status !== 'ACTIVE'}>
                <Sparkles className="size-3.5" /> {deriving ? '派生中…' : '派生 Action Plan'}
              </Button>
            </div>
            {derivedPlan && (
              <div className="mt-3">
                <p className="mb-1 text-xs font-medium text-muted-foreground">派生结果（Command IR）</p>
                <CommandDiff before={null} after={derivedPlan} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
