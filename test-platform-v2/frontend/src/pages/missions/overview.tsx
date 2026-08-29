import { toast } from 'sonner'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { fetchMission, MISSION_STATUS_LABELS, MISSION_TYPE_LABELS } from '@/api/missions'
import { missionKeys } from '@/lib/queryClient'
import { Inbox, Bug } from '@/lib/icons'
import { useAuthStore } from '@/stores/auth'
import { AiDebugDrawer, AI_VIEW_DEBUG_PERMISSION } from './AiDebugDrawer'

export default function MissionOverviewPage() {
  const { id } = useParams()
  const missionId = Number(id)
  // (v331-remediation-2 B3 / V30-100) 与 MissionLayout 共享 detail 缓存（原双请求消除）
  const { data: mission, isLoading, error } = useQuery({
    queryKey: missionKeys.detail(missionId),
    queryFn: ({ signal }) => fetchMission(missionId, signal),
    enabled: Number.isFinite(missionId) && missionId > 0,
  })
  const [debugOpen, setDebugOpen] = useState(false)
  // V30-085：AI Debug Drawer 仅 permission 可见
  const canViewAiDebug = useAuthStore((s) => s.permissions).includes(
    AI_VIEW_DEBUG_PERMISSION,
  )

  useEffect(() => {
    if (error) toast.error(error instanceof Error ? error.message : '加载失败')
  }, [error])

  useDocumentTitle(mission ? `概览 · ${mission.title}` : '概览')

  if (isLoading && !mission) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (!mission) {
    return <div className="p-10 text-center text-muted-foreground">任务不存在或已归档。</div>
  }

  const statusMeta = MISSION_STATUS_LABELS[mission.status]

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">类型</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {MISSION_TYPE_LABELS[mission.mission_type] ?? mission.mission_type}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">状态</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl">
            <Badge variant="secondary" className={statusMeta?.color}>
              {statusMeta?.label ?? mission.status}
            </Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">验收</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl">
            <Badge variant="outline">{mission.acceptance_status}</Badge>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Mission 主链</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-3">
          <div className="rounded-lg border p-3">
            <p className="text-muted-foreground">1. 资料 Sources</p>
            <p className="mt-1 text-muted-foreground">导入 PRD / OpenAPI / 需求链接</p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-muted-foreground">2. 范围 Scope Review</p>
            <p className="mt-1 text-muted-foreground">AI 分析 → Tester 评审</p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-muted-foreground">3. 契约 Contract</p>
            <p className="mt-1 text-muted-foreground">解决歧义 → Freeze 标准答案</p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-muted-foreground">4. 场景 Scenario</p>
            <p className="mt-1 text-muted-foreground">生成统一 TestScenario + Oracle</p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-muted-foreground">5. 执行 / 回放</p>
            <p className="mt-1 text-muted-foreground">Runtime → Evidence → Replay</p>
          </div>
          <div className="rounded-lg border p-3">
            <p className="text-muted-foreground">6. 验收 Acceptance</p>
            <p className="mt-1 text-muted-foreground">质量门禁 → Acceptance Report</p>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        {canViewAiDebug && (
          <Button
            variant="ghost"
            size="sm"
            aria-label="查看 AI 调试信息"
            onClick={() => setDebugOpen(true)}
          >
            <Bug className="size-4" /> AI 调试
          </Button>
        )}
        <Button variant="ghost" size="sm">
          <Inbox className="size-4" /> 归档
        </Button>
      </div>

      {canViewAiDebug && (
        <AiDebugDrawer
          missionId={missionId}
          open={debugOpen}
          onOpenChange={setDebugOpen}
        />
      )}
    </div>
  )
}
