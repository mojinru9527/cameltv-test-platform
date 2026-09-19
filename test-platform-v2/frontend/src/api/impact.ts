import api from './client'

/**
 * 影响面查询（Batch 260 / B3-3）。
 *
 * 回答 09 方案 §2.4 的唯一知识问题：**这个版本改了哪些模块 → 要跑哪些用例 → 上次跑得怎么样**。
 * 控制面只做聚合与检索；执行与推理都在别处（ADR-0026）。
 */

export interface ImpactCaseItem {
  case_id: number
  title: string
  module: string
  case_type: string
  ref: string
}

export interface ImpactLastRun {
  case_id: number
  plan_id: number
  status: string
  executed_at: string | null
  ref: string
}

export interface ImpactResult {
  project_id: number
  query: { module: string; version: string }
  affected_modules: string[]
  cases: { functional: ImpactCaseItem[]; api: ImpactCaseItem[]; ui: ImpactCaseItem[] }
  counts: {
    affected_modules: number
    functional: number
    api: number
    ui: number
    cases_total: number
    gaps: number
  }
  last_runs: ImpactLastRun[]
  gaps: string[]
  refs: { modules: string[]; cases: string[] }
  reason?: string
}

export async function fetchWhatToRun(
  params: { module: string; version?: string },
  signal?: AbortSignal,
): Promise<ImpactResult> {
  return api.get('/impact/what-to-run', { params, signal })
}
