import { Badge } from '@/ui'
import { Card } from '@/components/ui/card'

// ── Batch 191：团队进度树（只读展示 team_json 快照，不经 Markdown 渲染） ──

// 团队内部任务状态词表（插件 team.json 字段，与 dsh_task.status 无关，单独映射）
export const TEAM_TASK_STATUS_BADGE: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: 'bg-muted text-muted-foreground' },
  claimed: { label: '已认领', color: 'bg-muted text-muted-foreground' },
  in_progress: { label: '执行中', color: 'bg-status-info-muted text-status-info' },
  completed: { label: '已完成', color: 'bg-status-success-muted text-status-success' },
  failed: { label: '失败', color: 'bg-status-danger-muted text-status-danger' },
  cancelled: { label: '已取消', color: 'bg-muted text-muted-foreground' },
}

export const MEMBER_STATUS_BADGE: Record<string, string> = { active: '在队', removed: '已移除' }

// 团队阶段（由 dsh_task.status 推导，用于团队头）
const TEAM_STAGE: Record<string, string> = {
  pending: '等待认领',
  running: '执行中',
  success: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

interface TeamProgressProps {
  teamJson: Record<string, any>
  status: string
  outputText: string
}

/** 成员当前任务：首个 in_progress 且 assignee==该成员 的 task.subject；无则「—」 */
function currentTaskFor(memberId: string, tasks: any[]): string {
  const t = tasks?.find(
    (task) => task?.status === 'in_progress' && task?.assignee === memberId,
  )
  return t?.subject ?? '—'
}

function doneRatio(memberId: string, tasks: any[]): number {
  if (!Array.isArray(tasks) || tasks.length === 0) return 0
  const mine = tasks.filter((t) => t?.assignee === memberId)
  if (mine.length === 0) return 0
  return mine.filter((t) => t?.status === 'completed').length / mine.length
}

export default function TeamProgress({ teamJson, status, outputText }: TeamProgressProps) {
  const members: any[] = Array.isArray(teamJson.members) ? teamJson.members : []
  const tasks: any[] = Array.isArray(teamJson.tasks) ? teamJson.tasks : []
  const conclusion: string | undefined = teamJson.conclusion

  return (
    <div className="space-y-4" data-testid="team-progress">
      {/* 团队头 */}
      <div className="flex items-center gap-2">
        <Badge className="bg-status-info-muted text-status-info">{TEAM_STAGE[status] ?? status}</Badge>
        <span className="font-medium">{teamJson.name || '团队'}</span>
        {teamJson.id && <span className="text-xs text-muted-foreground">#{teamJson.id}</span>}
      </div>

      {/* 成员卡区 */}
      {members.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {members.map((m) => {
            const done = doneRatio(m?.id, tasks)
            const badge = MEMBER_STATUS_BADGE[m?.status] ?? m?.status ?? '—'
            return (
              <Card key={m?.id ?? m?.name} className="p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium truncate">{m?.name || '—'}</span>
                  <Badge variant="outline" className="text-xs">{badge}</Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{m?.role || '—'}</p>
                <div className="mt-2 h-2 rounded bg-muted overflow-hidden">
                  <div
                    className="h-full rounded bg-status-info transition-all"
                    style={{ width: `${Math.round(done * 100)}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-1.5 truncate" title={currentTaskFor(m?.id, tasks)}>
                  当前：{currentTaskFor(m?.id, tasks)}
                </p>
              </Card>
            )
          })}
        </div>
      )}

      {/* 任务列表区（按依赖深度排序：dependencies 长度升序） */}
      {tasks.length > 0 && (
        <div className="space-y-1" data-testid="team-tasks">
          {[...tasks]
            .sort((a, b) => (a?.dependencies?.length ?? 0) - (b?.dependencies?.length ?? 0))
            .map((t, i) => {
              const badge = TEAM_TASK_STATUS_BADGE[t?.status] ?? { label: t?.status ?? '—', color: '' }
              return (
                <div key={t?.id ?? i} className="flex items-center gap-2 py-2 text-sm">
                  <Badge className={badge.color}>{badge.label}</Badge>
                  <span className="truncate flex-1">{t?.subject || '—'}</span>
                  {t?.assignee && (
                    <span className="text-xs text-muted-foreground shrink-0">{t.assignee}</span>
                  )}
                  {Array.isArray(t?.dependencies) && t.dependencies.length > 0 && (
                    <span className="text-xs text-muted-foreground shrink-0">
                      依赖 #{t.dependencies.join(' #')}
                    </span>
                  )}
                </div>
              )
            })}
        </div>
      )}

      {/* 团队结论区（team_json.conclusion 优先；否则取 output_text 尾部） */}
      {(conclusion || outputText) && (
        <div>
          <h4 className="font-medium mb-1">团队结论</h4>
          <pre className="text-xs bg-muted p-3 rounded-md whitespace-pre-wrap font-mono max-h-64 overflow-y-auto">
            {conclusion || outputText}
          </pre>
        </div>
      )}

      {/* 截断提示 */}
      {teamJson._truncated === true && (
        <p className="text-xs text-status-warning bg-status-warning-muted rounded-md px-3 py-1.5">
          进度数据已截断
        </p>
      )}
    </div>
  )
}
