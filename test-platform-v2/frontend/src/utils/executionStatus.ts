/**
 * 执行状态统一映射（Batch 182 / FIX-173-P1-06）
 *
 * 后端 DB/API 已统一词表：pending | running | passed | failed | skipped | cancelled | blocked
 * 本模块提供：
 *  - EXEC_STATUS_LABEL：新旧双值 → 中文标签（历史数据/过渡期兼容展示）
 *  - normalizeExecStatus(v)：旧值归一为规范值（展示层用规范值查映射）
 */
export const EXEC_STATUS_LABEL: Record<string, string> = {
  // 规范值
  pending: '待执行',
  running: '执行中',
  passed: '通过',
  failed: '失败',
  skipped: '跳过',
  cancelled: '已取消',
  blocked: '阻塞',
  // 历史/过渡值（后端已迁移，兼容旧前端缓存与旧数据）
  pass: '通过',
  fail: '失败',
  skip: '跳过',
  block: '阻塞',
  success: '通过',
  done: '通过',
  completed: '通过',
  idle: '待执行',
}

/** 旧值 → 规范值（与后端 app/core/execution_status.py 保持一致） */
const LEGACY_TO_CANONICAL: Record<string, string> = {
  pass: 'passed',
  fail: 'failed',
  skip: 'skipped',
  block: 'blocked',
  success: 'passed',
  done: 'passed',
  completed: 'passed',
  idle: 'pending',
}

export function normalizeExecStatus(value?: string | null): string {
  if (!value) return value ?? ''
  if (LEGACY_TO_CANONICAL[value]) return LEGACY_TO_CANONICAL[value]
  return value
}

/** 展示标签：旧值/新值都可用 */
export function execStatusLabel(value?: string | null): string {
  return EXEC_STATUS_LABEL[value ?? ''] ?? value ?? ''
}
