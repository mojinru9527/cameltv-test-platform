import type { BadgeTone, StatusVariant } from '@/ui'

/**
 * 版本验收任务的展示字典（Batch 230 / DEF-20260905-002、-003）。
 *
 * `task.status` / `verdict` / `run.status` / `failure.kind` 的取值都落在
 * `StatusVariant` 与 `SeverityVariant` 联合类型之外，`StatusBadge` 无法直接
 * 消费；集中在此避免列表页与详情页各写一份、裸英文状态标签反复复发。
 */
export const TASK_STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  plan_review: '待评审',
  approved: '已批准',
  executing: '执行中',
  executed: '已执行',
  verdict: '待结论',
  released: '已结束',
  blocked: '已阻塞',
  cancelled: '已取消',
}

export const TASK_STATUS_TONE: Record<string, BadgeTone> = {
  draft: 'neutral',
  plan_review: 'info',
  approved: 'success',
  executing: 'info',
  executed: 'neutral',
  verdict: 'warning',
  released: 'success',
  blocked: 'warning',
  cancelled: 'neutral',
}

/** 对照后端 `version_task_service.VALID_VERDICTS`；空串表示尚未下结论。 */
export const VERDICT_LABEL: Record<string, string> = {
  pass: '放行',
  blocked: '打回',
  conditional: '有条件放行',
}

/** 对照后端 `version_task_service.FAILURE_KINDS`（script/data 目前无产出路径，走 fallback）。 */
export const FAILURE_KIND_LABEL: Record<string, string> = {
  business: '业务失败',
  environment: '环境阻塞',
  plan: '方案无可执行项',
}

/** 只有 business 是质量问题；environment/plan 是「没跑起来」，染红会误导分诊。 */
export const FAILURE_KIND_TONE: Record<string, BadgeTone> = {
  business: 'danger',
  environment: 'warning',
  plan: 'warning',
}

/**
 * `run.status` 取值是 `done|failed|blocked|running|pending`，`done`/`failed`
 * 不在 `StatusVariant` 内，而 `StatusBadge.variant` 必填且类型受限，故须显式映射。
 */
export const RUN_STATUS_TO_VARIANT: Record<string, StatusVariant> = {
  done: 'pass',
  failed: 'fail',
  blocked: 'blocked',
  running: 'running',
  pending: 'pending',
}
