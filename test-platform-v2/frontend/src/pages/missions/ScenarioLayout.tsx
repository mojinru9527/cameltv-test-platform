import { useState } from 'react'
import { NavLink, Outlet, useParams } from 'react-router'
import { toast } from 'sonner'
import { Badge, Skeleton } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { fetchMission, MISSION_STATUS_LABELS, type Mission } from '@/api/missions'
import { fetchScenario, type ScenarioDetail } from '@/api/scenarios'
import { cn } from '@/lib/utils'

const SCENARIO_TABS = [
  { key: 'manual', label: '手工执行', path: 'manual' },
  { key: 'observe', label: '观察', path: 'observe' },
  { key: 'action-plan', label: 'Action Plan', path: 'action-plan' },
  { key: 'hybrid-run', label: 'Hybrid Run', path: 'hybrid-run' },
]

/**
 * Scenario-scoped layout for AITDE V3.3 pages (manual / observe / action-plan /
 * hybrid-run). Renders the mission + scenario header and a scenario tab bar.
 */
export default function ScenarioLayout() {
  const { missionId, scenarioId } = useParams()
  const missionIdNum = Number(missionId)
  const scenarioIdNum = Number(scenarioId)
  const [mission, setMission] = useState<Mission | null>(null)
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useDocumentTitle(scenario ? scenario.title : '场景执行')

  useAbortableEffect((signal) => {
    if (!missionIdNum || !scenarioIdNum) return
    setLoading(true)
    fetchMission(missionIdNum, signal)
      .then(setMission)
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载任务失败')
      })
    fetchScenario(scenarioIdNum)
      .then(setScenario)
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载场景失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionIdNum, scenarioIdNum])

  if (loading && (!mission || !scenario)) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-10 w-96" />
        <Skeleton className="h-8 w-full" />
      </div>
    )
  }

  if (!scenario) {
    return <div className="p-10 text-center text-muted-foreground">场景不存在或已删除。</div>
  }

  const missionStatus = mission ? MISSION_STATUS_LABELS[mission.status] : null

  return (
    <div className="space-y-4 p-4">
      <div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span className="font-mono text-xs">{scenario.scenario_key}</span>
          {mission && (
            <>
              <span>·</span>
              <span>{mission.title}</span>
              {missionStatus && (
                <Badge variant="secondary" className={missionStatus.color}>
                  {missionStatus.label}
                </Badge>
              )}
            </>
          )}
        </div>
        <h1 className="mt-1 text-xl font-semibold tracking-[-0.02em]">{scenario.title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{scenario.business_goal}</p>
      </div>

      <div className="flex flex-wrap gap-1 border-b">
        {SCENARIO_TABS.map((tab) => (
          <NavLink
            key={tab.key}
            to={`/missions/${missionIdNum}/scenarios/${scenarioIdNum}/${tab.path}`}
            className={({ isActive }) =>
              cn(
                '-mb-px border-b-2 px-3 py-2 text-sm font-medium',
                isActive
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </div>

      <Outlet />
    </div>
  )
}
