import { toast } from 'sonner'
import { useParams } from 'react-router'
import { useState } from 'react'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/ui'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import useAbortableEffect from '@/hooks/useAbortableEffect'
import {
  fetchMission,
  MISSION_STATUS_LABELS,
  MISSION_TYPE_LABELS,
  type Mission,
} from '@/api/missions'
import { Inbox } from '@/lib/icons'

export default function MissionOverviewPage() {
  const { id } = useParams()
  const missionId = Number(id)
  const [mission, setMission] = useState<Mission | null>(null)
  const [loading, setLoading] = useState(true)

  useDocumentTitle(mission ? `概览 · ${mission.title}` : '概览')

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

      <div className="flex justify-end">
        <Button variant="ghost" size="sm">
          <Inbox className="size-4" /> 归档
        </Button>
      </div>
    </div>
  )
}
