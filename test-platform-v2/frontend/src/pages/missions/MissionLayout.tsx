import { NavLink, Outlet, useParams } from 'react-router'
import { toast } from 'sonner'
import { Badge, Skeleton } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import { useState } from 'react'
import { fetchMission, MISSION_STATUS_LABELS, MISSION_TYPE_LABELS, type Mission } from '@/api/missions'
import { cn } from '@/lib/utils'

const TABS = [
  { key: 'overview', label: '概览', path: 'overview' },
  { key: 'sources', label: '资料', path: 'sources' },
  { key: 'scope', label: '范围', path: 'scope' },
  { key: 'contract', label: '契约', path: 'contract' },
  { key: 'scenarios', label: '场景', path: 'scenarios' },
  { key: 'executions', label: '执行', path: 'executions' },
]

export default function MissionLayout() {
  const { id } = useParams()
  const missionId = Number(id)
  const [mission, setMission] = useState<Mission | null>(null)
  const [loading, setLoading] = useState(true)

  useDocumentTitle(mission ? mission.title : '测试任务')

  useAbortableEffect((signal) => {
    if (!missionId) return
    setLoading(true)
    fetchMission(missionId, signal)
      .then(setMission)
      .catch((err) => {
        if (!(err?.code === 'ERR_CANCELED')) toast.error(err.message || '加载失败')
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
  }, [missionId])

  if (loading && !mission) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-10 w-96" />
        <Skeleton className="h-8 w-full" />
      </div>
    )
  }

  if (!mission) {
    return <div className="p-10 text-center text-muted-foreground">任务不存在或已归档。</div>
  }

  const statusMeta = MISSION_STATUS_LABELS[mission.status]

  return (
    <div className="space-y-4 p-4">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span className="font-mono text-xs">{mission.mission_key}</span>
          <span>·</span>
          <span>{MISSION_TYPE_LABELS[mission.mission_type] ?? mission.mission_type}</span>
          {mission.version_label && (
            <>
              <span>·</span>
              <span>{mission.version_label}</span>
            </>
          )}
        </div>
        <h1 className="mt-1 text-xl font-semibold tracking-[-0.02em]">{mission.title}</h1>
        <div className="mt-2 flex items-center gap-2">
          <Badge variant="secondary" className={statusMeta?.color}>
            {statusMeta?.label ?? mission.status}
          </Badge>
          <Badge variant="outline">{mission.acceptance_status}</Badge>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 border-b">
        {TABS.map((tab) => (
          <NavLink
            key={tab.key}
            to={`/missions/${mission.id}/${tab.path}`}
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
