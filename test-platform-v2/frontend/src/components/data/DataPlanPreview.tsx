import { Badge, Button } from '@/ui'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardAction,
} from '@/components/ui/card'
import { Check, ShieldCheck, Lock } from '@/lib/icons'
import { DataPlanRiskBadge } from './DataPlanRiskBadge'
import { SuccessStageBadge } from '@/components/trust/SuccessStageBadge'
import {
  DATA_PLAN_STATUS_LABELS,
  DATA_PLAN_STEP_TYPE_LABELS,
  DATA_PLAN_STRATEGY_LABELS,
  type DataPlan,
} from '@/api/dataPlans'

export interface DataPlanPreviewProps {
  plan: DataPlan
  onApprove?: () => void
  approving?: boolean
}

/**
 * Ordered preview of a generated data plan. High-risk (P0/P1) plans require
 * an explicit manual approval; the Approve button is surfaced only in that case.
 */
export function DataPlanPreview({ plan, onApprove, approving }: DataPlanPreviewProps) {
  const statusMeta = DATA_PLAN_STATUS_LABELS[plan.status]
  const isHighRisk = plan.risk_level === 'P0' || plan.risk_level === 'P1'
  const needsApproval = isHighRisk && plan.status !== 'APPROVED'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span>数据计划 #{plan.id}</span>
          <DataPlanRiskBadge riskLevel={plan.risk_level} />
        </CardTitle>
        <CardDescription>
          策略 {DATA_PLAN_STRATEGY_LABELS[plan.strategy] ?? plan.strategy} · 版本 {plan.scenario_version_id}
          {plan.environment_id ? ` · 环境 ${plan.environment_id}` : ''}
        </CardDescription>
        <CardAction className="flex flex-col items-end gap-1.5">
          <SuccessStageBadge plan={plan} />
          <Badge variant="secondary" className={statusMeta?.color}>
            {statusMeta?.label ?? plan.status}
          </Badge>
        </CardAction>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <p className="text-xs text-muted-foreground">策略</p>
            <p className="font-medium">{DATA_PLAN_STRATEGY_LABELS[plan.strategy] ?? plan.strategy}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">风险</p>
            <DataPlanRiskBadge riskLevel={plan.risk_level} />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">创建</p>
            <p className="font-mono text-xs">{plan.created_at ?? '—'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">审批</p>
            <p className="font-mono text-xs">
              {plan.approved_by ? `#${plan.approved_by}` : '未审批'}
            </p>
          </div>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium">执行步骤</p>
          <ol className="space-y-2">
            {plan.steps.length === 0 ? (
              <li className="rounded-md border border-dashed px-3 py-3 text-center text-xs text-muted-foreground">
                尚无步骤
              </li>
            ) : (
              plan.steps
                .slice()
                .sort((a, b) => a.sequence - b.sequence)
                .map((step) => (
                  <li
                    key={step.id}
                    className="flex items-start gap-3 rounded-md border px-3 py-2"
                  >
                    <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-md bg-muted font-mono text-xs">
                      {step.sequence}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">
                          {DATA_PLAN_STEP_TYPE_LABELS[step.step_type] ?? step.step_type}
                        </span>
                        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground/80">
                          {step.driver}
                        </code>
                        <Badge variant="outline" className="text-xs">{step.status}</Badge>
                      </div>
                      {step.command_json && (
                        <pre className="mt-1 overflow-x-auto rounded bg-muted/50 p-2 font-mono text-[11px] text-muted-foreground">
                          {JSON.stringify(step.command_json, null, 2)}
                        </pre>
                      )}
                      {step.compensation_json && (
                        <pre className="mt-1 overflow-x-auto rounded bg-muted/50 p-2 font-mono text-[11px] text-muted-foreground">
                          补偿: {JSON.stringify(step.compensation_json)}
                        </pre>
                      )}
                    </div>
                  </li>
                ))
            )}
          </ol>
        </div>

        <div className="flex items-center justify-between rounded-md border px-3 py-2">
          <div className="flex items-center gap-2 text-sm">
            {needsApproval ? (
              <>
                <ShieldCheck className="size-4 text-status-warning" />
                <span className="text-muted-foreground">高风险计划需人工审批后才能执行。</span>
              </>
            ) : isHighRisk ? (
              <>
                <Check className="size-4 text-status-success" />
                <span className="text-muted-foreground">高风险计划已批准。</span>
              </>
            ) : (
              <>
                <Check className="size-4 text-status-success" />
                <span className="text-muted-foreground">低风险计划无需人工审批。</span>
              </>
            )}
          </div>
          {needsApproval && (
            <Button disabled={approving} onClick={onApprove}>
              <Lock className="size-4" /> {approving ? '审批中…' : '审批通过'}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
