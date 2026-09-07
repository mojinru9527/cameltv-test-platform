import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  fetchMission,
  fetchMissionLifecycle,
  MISSION_STATUS_LABELS,
  MISSION_TYPE_LABELS,
  type MissionLifecycleCase,
  type MissionLifecycleStage,
} from '@/api/missions'
import OutcomeBadge from '@/components/executions/OutcomeBadge'
import { ErrorState } from '@/components/state'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { AlertTriangle, Bug, CheckCircle2, Circle, History, Inbox } from '@/lib/icons'
import { missionKeys } from '@/lib/queryClient'
import { useAuthStore } from '@/stores/auth'
import { Badge, Button, Card, CardContent, Skeleton, cn } from '@/ui'
import { AiDebugDrawer, AI_VIEW_DEBUG_PERMISSION } from './AiDebugDrawer'

const CASE_TYPE_LABELS: Record<string, string> = {
  FUNCTIONAL: '功能',
  API: '接口',
  UI: 'UI 自动化',
  UNCLASSIFIED: '未分类',
}

const REQUIREMENT_ROLE_LABELS: Record<string, string> = {
  NEW: '新增',
  CHANGED: '变更',
  IMPACTED_BASELINE: '受影响基线',
  UNCLASSIFIED: '未分类',
}

const RETEST_LABELS: Record<string, string> = {
  NOT_REQUIRED: '无需复验',
  PENDING_RETEST: '待复验',
  RETEST_PASSED: '复验通过',
  RETEST_FAILED: '复验失败',
}

const ACCEPTANCE_STATUS_LABELS: Record<string, string> = {
  PASS: '通过',
  FAIL: '未通过',
  NOT_EVALUATED: '未评估',
  BLOCKED: '已阻塞',
}

function StageStatus({ stage }: { stage: MissionLifecycleStage }) {
  const complete = stage.status === 'COMPLETE'
  const inProgress = stage.status === 'IN_PROGRESS'
  const Icon = complete ? CheckCircle2 : inProgress ? AlertTriangle : Circle
  return (
    <div className="flex min-w-0 items-start gap-2.5">
      <Icon
        aria-hidden="true"
        className={cn(
          'mt-0.5 size-4 shrink-0',
          complete && 'text-status-success',
          inProgress && 'text-status-warning',
          !complete && !inProgress && 'text-muted-foreground',
        )}
      />
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{stage.label}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {stage.completed} / {stage.total}
        </p>
      </div>
    </div>
  )
}

function RetestBadge({ value }: { value: string }) {
  const isPassed = value === 'RETEST_PASSED'
  const isFailed = value === 'RETEST_FAILED'
  return (
    <Badge
      variant="secondary"
      className={cn(
        isPassed && 'bg-status-success-muted text-status-success',
        isFailed && 'bg-destructive/10 text-destructive',
      )}
    >
      {RETEST_LABELS[value] ?? value}
    </Badge>
  )
}

function CaseRow({ item }: { item: MissionLifecycleCase }) {
  return (
    <div className="grid gap-3 border-b px-3 py-3 last:border-b-0 md:grid-cols-[minmax(12rem,2fr)_minmax(8rem,1fr)_minmax(10rem,1.2fr)_minmax(14rem,1.6fr)] md:items-center">
      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-2">
          <Badge variant="outline">{CASE_TYPE_LABELS[item.case_type] ?? item.case_type}</Badge>
          <p className="truncate text-sm font-medium" title={item.title}>{item.title}</p>
        </div>
        <p className="mt-1 truncate text-xs text-muted-foreground" title={item.module_key ?? item.scenario_key}>
          {item.module_key || item.scenario_key}
        </p>
      </div>
      <div className="flex flex-wrap gap-1.5 text-xs">
        <Badge variant="secondary">
          {REQUIREMENT_ROLE_LABELS[item.requirement_role] ?? item.requirement_role}
        </Badge>
        <span className="self-center text-muted-foreground">来源 {item.source_ref_count}</span>
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <span>执行 {item.run_count}</span>
        <span>步骤 {item.step_count}</span>
        <span>断言 {item.assertion_count}</span>
        <span>证据 {item.verified_evidence_count}/{item.evidence_count}</span>
        <span>回放 {item.replay_count}</span>
        <span>缺陷 {item.defect_count}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2 md:justify-end">
        <OutcomeBadge outcome={item.latest_outcome} />
        <RetestBadge value={item.retest_status} />
        {item.latest_run_id && item.replay_count > 0 && (
          <Link
            to={`/executions/${item.latest_run_id}/replay`}
            aria-label={`回放 Run #${item.latest_run_id}`}
            title={`回放 Run #${item.latest_run_id}`}
            className="inline-flex size-8 items-center justify-center rounded-lg hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <History className="size-4" />
          </Link>
        )}
      </div>
    </div>
  )
}

export default function MissionOverviewPage() {
  const { id } = useParams()
  const missionId = Number(id)
  const enabled = Number.isFinite(missionId) && missionId > 0
  const missionQuery = useQuery({
    queryKey: missionKeys.detail(missionId),
    queryFn: ({ signal }) => fetchMission(missionId, signal),
    enabled,
  })
  const lifecycleQuery = useQuery({
    queryKey: missionKeys.lifecycle(missionId),
    queryFn: ({ signal }) => fetchMissionLifecycle(missionId, signal),
    enabled,
  })
  const [debugOpen, setDebugOpen] = useState(false)
  const canViewAiDebug = useAuthStore((state) => state.hasPerm(AI_VIEW_DEBUG_PERMISSION))

  useEffect(() => {
    if (missionQuery.error) {
      toast.error(missionQuery.error instanceof Error ? missionQuery.error.message : '任务加载失败')
    }
  }, [missionQuery.error])

  const mission = missionQuery.data
  const lifecycle = lifecycleQuery.data
  useDocumentTitle(mission ? `概览 · ${mission.title}` : '概览')

  if ((missionQuery.isLoading || lifecycleQuery.isLoading) && (!mission || !lifecycle)) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (lifecycleQuery.error) {
    return (
      <ErrorState
        title="全链路数据加载失败"
        error={lifecycleQuery.error instanceof Error ? lifecycleQuery.error : null}
        onRetry={() => void lifecycleQuery.refetch()}
      />
    )
  }

  if (missionQuery.error || !mission || !lifecycle) {
    return (
      <ErrorState
        title="任务加载失败"
        error={missionQuery.error instanceof Error ? missionQuery.error : null}
        onRetry={() => void missionQuery.refetch()}
      />
    )
  }

  const statusMeta = MISSION_STATUS_LABELS[mission.status]
  const caseTypes = lifecycle.coverage.case_types
  const requirementRoles = lifecycle.coverage.requirement_roles

  return (
    <div className="space-y-5">
      <section className="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">
            {MISSION_TYPE_LABELS[mission.mission_type] ?? mission.mission_type}
          </Badge>
          <Badge variant="secondary" className={statusMeta?.color}>
            {statusMeta?.label ?? mission.status}
          </Badge>
          <Badge variant="outline">
            验收 {ACCEPTANCE_STATUS_LABELS[lifecycle.mission.acceptance_status] ?? lifecycle.mission.acceptance_status}
          </Badge>
          {lifecycle.version_task && (
            <span className="text-sm text-muted-foreground">
              版本 {lifecycle.version_task.version}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
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
      </section>

      <section aria-labelledby="test-phases-title">
        <div className="mb-2 flex items-baseline justify-between gap-3">
          <h2 id="test-phases-title" className="text-sm font-semibold">测试阶段</h2>
          <span className="text-xs text-muted-foreground">同一版本任务的三段验收事实</span>
        </div>
        {lifecycle.phases.length > 0 ? (
          <div className="grid gap-2 sm:grid-cols-3">
            {lifecycle.phases.map((phase) => (
              <Link
                key={phase.mission_id}
                to={`/missions/${phase.mission_id}/overview`}
                aria-current={phase.is_current ? 'step' : undefined}
                className={cn(
                  'min-w-0 border-l-2 px-3 py-2 transition-colors hover:bg-muted/60',
                  phase.is_current ? 'border-primary bg-muted/40' : 'border-border',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium">{phase.label}</span>
                  {phase.is_current && <Badge variant="secondary">当前</Badge>}
                </div>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {MISSION_STATUS_LABELS[phase.status]?.label ?? phase.status}
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <p className="py-5 text-sm text-muted-foreground">当前任务尚未关联版本测试阶段。</p>
        )}
      </section>

      <section aria-labelledby="lifecycle-title" className="border-y py-4">
        <div className="mb-3 flex items-baseline justify-between gap-3">
          <h2 id="lifecycle-title" className="text-sm font-semibold">AI 六阶段主链</h2>
          <span className="text-xs text-muted-foreground">数据来自任务实际产物</span>
        </div>
        <div className="grid gap-x-4 gap-y-3 sm:grid-cols-3 xl:grid-cols-6">
          {lifecycle.stages.map((stage) => <StageStatus key={stage.key} stage={stage} />)}
        </div>
      </section>

      <section aria-labelledby="coverage-title">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="coverage-title" className="text-sm font-semibold">用例覆盖</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              共 {lifecycle.totals.cases} 条，已执行 {lifecycle.totals.executed_cases} 条
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">功能 {caseTypes.FUNCTIONAL}</Badge>
            <Badge variant="outline">接口 {caseTypes.API}</Badge>
            <Badge variant="outline">UI 自动化 {caseTypes.UI}</Badge>
            <span className="mx-1 hidden h-5 w-px bg-border sm:block" aria-hidden="true" />
            <Badge variant="secondary">新增 {requirementRoles.NEW}</Badge>
            <Badge variant="secondary">变更 {requirementRoles.CHANGED}</Badge>
            <Badge variant="secondary">受影响基线 {requirementRoles.IMPACTED_BASELINE}</Badge>
          </div>
        </div>

        {lifecycle.gaps.length > 0 && (
          <div className="mb-3 border-l-2 border-status-warning bg-status-warning-muted px-3 py-2 text-sm text-status-warning">
            {lifecycle.gaps.join('；')}
          </div>
        )}

        <Card className="overflow-hidden">
          <CardContent className="p-0">
            <div className="hidden grid-cols-[minmax(12rem,2fr)_minmax(8rem,1fr)_minmax(10rem,1.2fr)_minmax(14rem,1.6fr)] border-b bg-muted/40 px-3 py-2 text-xs font-medium text-muted-foreground md:grid">
              <span>用例与模块</span>
              <span>需求归属</span>
              <span>执行事实</span>
              <span className="text-right">结论与复验</span>
            </div>
            {lifecycle.cases.length > 0 ? (
              lifecycle.cases.map((item) => <CaseRow key={item.scenario_version_id} item={item} />)
            ) : (
              <p className="px-4 py-10 text-center text-sm text-muted-foreground">尚未生成测试用例。</p>
            )}
          </CardContent>
        </Card>
      </section>

      <section aria-labelledby="supporting-facts-title" className="border-t pt-4">
        <div className="mb-3 flex items-baseline justify-between gap-3">
          <h2 id="supporting-facts-title" className="text-sm font-semibold">验证资产</h2>
          <span className="text-xs text-muted-foreground">
            变化 {lifecycle.artifacts.change_items} · 影响 {lifecycle.artifacts.impact_runs} · 追溯 {lifecycle.artifacts.lineage_edges} · 缺口 {lifecycle.artifacts.gap_candidates}
          </span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {lifecycle.supporting_stages.map((stage) => {
            const path = stage.key === 'builds'
              ? 'builds'
              : stage.key === 'changes'
                ? 'changes'
                : stage.key === 'impact'
                  ? 'impact'
                  : stage.key === 'lineage'
                    ? 'trace'
                    : 'gaps'
            return (
              <Link
                key={stage.key}
                to={`/missions/${missionId}/${path}`}
                className="min-h-16 border-l-2 border-border px-3 py-2 transition-colors hover:bg-muted/60"
              >
                <StageStatus stage={stage} />
              </Link>
            )
          })}
        </div>
      </section>

      {canViewAiDebug && (
        <AiDebugDrawer missionId={missionId} open={debugOpen} onOpenChange={setDebugOpen} />
      )}
    </div>
  )
}
