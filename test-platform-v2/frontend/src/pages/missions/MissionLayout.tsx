import { NavLink, Outlet, useParams } from 'react-router'
import { useEffect } from 'react'
import { toast } from 'sonner'
import { useQuery } from '@tanstack/react-query'
import { Badge, Skeleton } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  fetchMission,
  fetchMissionLifecycle,
  MISSION_STATUS_LABELS,
  MISSION_TYPE_LABELS,
} from '@/api/missions'
import { missionKeys } from '@/lib/queryClient'
import { cn } from '@/lib/utils'
import { AlertTriangle } from '@/lib/icons'

const TABS = [
  { key: 'overview', label: '概览', path: 'overview' },
  { key: 'sources', label: '资料', path: 'sources' },
  { key: 'scope', label: '范围', path: 'scope' },
  { key: 'contract', label: '契约', path: 'contract' },
  { key: 'scenarios', label: '场景', path: 'scenarios' },
  { key: 'executions', label: '执行', path: 'executions' },
  { key: 'builds', label: 'Build', path: 'builds' },
  { key: 'acceptance', label: '验收', path: 'acceptance' },
  { key: 'changes', label: '变化检测', path: 'changes' },
  { key: 'impact', label: '影响分析', path: 'impact' },
  { key: 'trace', label: 'Lineage', path: 'trace' },
  { key: 'gaps', label: '场景缺口', path: 'gaps' },
]

export default function MissionLayout() {
  const { id } = useParams()
  const missionId = Number(id)
  // (v331-remediation-2 B3 / V30-100) TanStack Query：detail 与 overview 共享缓存
  const { data: mission, isLoading, error } = useQuery({
    queryKey: missionKeys.detail(missionId),
    queryFn: ({ signal }) => fetchMission(missionId, signal),
    enabled: Number.isFinite(missionId) && missionId > 0,
  })
  const lifecycleQuery = useQuery({
    queryKey: missionKeys.lifecycle(missionId),
    queryFn: ({ signal }) => fetchMissionLifecycle(missionId, signal),
    enabled: Number.isFinite(missionId) && missionId > 0,
  })

  useEffect(() => {
    if (error) toast.error(error instanceof Error ? error.message : '加载失败')
  }, [error])

  useDocumentTitle(mission ? mission.title : '测试任务')

  if (isLoading && !mission) {
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
  const lifecycle = lifecycleQuery.data
  const acceptanceStatus = lifecycle?.mission.acceptance_status ?? mission.acceptance_status
  const acceptanceLabel = acceptanceStatus === 'PASS'
    ? '验收通过'
    : acceptanceStatus === 'FAIL'
      ? '验收失败'
      : '未验收'

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
        <h1 className="mt-1 text-xl font-semibold tracking-normal">{mission.title}</h1>
        <div className="mt-2 flex items-center gap-2">
          <Badge variant="secondary" className={statusMeta?.color}>
            {statusMeta?.label ?? mission.status}
          </Badge>
          <Badge variant="outline">{acceptanceLabel}</Badge>
        </div>
      </div>

      {lifecycle && lifecycle.integrity_status !== 'COMPLETE' && (
        <div className="flex items-start gap-2 border-l-2 border-status-warning bg-status-warning-muted px-3 py-2 text-sm text-status-warning">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>
            任务事实链不完整，不可判定为通过
            {!lifecycle.mission.acceptance_consistent && '；已忽略与 Quality Gate 不一致的历史验收状态'}
          </span>
        </div>
      )}

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
