import { aitdeV2 } from './missions'

// ── AITDE V3.8 AI QA Closed Loop domain types ──

export interface FailureHypothesis {
  id: number
  run_id: number
  hypothesis_type: string
  classification: string
  summary: string
  confidence: number
  evidence_refs: Record<string, unknown>[]
  suggested_checks: string[]
  model_ref?: string | null
  prompt_version?: string | null
  status: string
  reviewed_by?: number | null
  created_at: string | null
  outcome?: string | null
}

export interface FlakyCluster {
  id: number
  scenario_adapter_id: number
  cluster_key: string
  classification: string
  sample_size: number
  failure_rate: number
  confidence: number
  status: string
}

export interface AiSuggestion {
  id: number
  project_id: number
  mission_id?: number | null
  suggestion_type: string
  target_type: string
  target_id: number
  payload: Record<string, unknown>
  evidence_refs: Record<string, unknown>[]
  confidence: number
  status: string
}

export interface ScenarioGap {
  id: number
  mission_id: number
  gap_type: string
  title: string
  description: string
  source_refs: Record<string, unknown>[]
  evidence_refs: Record<string, unknown>[]
  risk_level: string
  confidence: number
  status: string
}

export interface ModelEvaluation {
  id: number
  evaluation_suite: string
  model_ref: string
  prompt_versions: string[]
  status: string
  metrics: Record<string, unknown>
  artifact_uri?: string | null
  created_at: string | null
}

export interface HumanFeedback {
  id: number
  project_id: number
  mission_id?: number | null
  target_type: string
  target_id: number
  feedback_type: string
  before?: Record<string, unknown> | null
  after?: Record<string, unknown> | null
  reason?: string | null
  created_by: number
}

export type ReviewAction = 'APPROVED' | 'REJECTED'

// ── Failure triage / hypothesis ──

export function triageRun(
  runId: number,
  payload: {
    context?: Record<string, unknown>
    model_ref?: string | null
    prompt_version?: string | null
  },
): Promise<FailureHypothesis> {
  return aitdeV2.post(`/runs/${runId}/triage`, payload)
}

export function listHypotheses(runId: number, signal?: AbortSignal): Promise<FailureHypothesis[]> {
  return aitdeV2.get(`/runs/${runId}/hypotheses`, { signal })
}

export function reviewHypothesis(
  hypothesisId: number,
  payload: { status: string; reviewed_by?: number | null; reason?: string | null },
): Promise<FailureHypothesis> {
  return aitdeV2.post(`/hypotheses/${hypothesisId}/review`, payload)
}

// ── Healing ──

export function applyHealing(
  proposalId: number,
  payload: { approved_by?: number | null; note?: string | null },
): Promise<{
  command_plan_id: number
  command_plan_version_id: number
  version_no: number
  status: string
  old_retained: boolean
}> {
  return aitdeV2.post(`/healing-proposals/${proposalId}/apply`, payload)
}

// ── Flaky / stability ──

export function listFlaky(
  scenarioAdapterId?: number | null,
  signal?: AbortSignal,
): Promise<FlakyCluster[]> {
  const qs = scenarioAdapterId ? `?scenario_adapter_id=${scenarioAdapterId}` : ''
  return aitdeV2.get(`/flaky${qs}`, { signal })
}

export function scenarioStability(scenarioId: number, signal?: AbortSignal): Promise<{ scenario_id: number; clusters: FlakyCluster[] }> {
  return aitdeV2.get(`/scenarios/${scenarioId}/stability`, { signal })
}

// ── Suggestion inbox ──

export function listAiSuggestions(
  status?: string | null,
  signal?: AbortSignal,
): Promise<AiSuggestion[]> {
  const qs = status ? `?status=${status}` : ''
  return aitdeV2.get(`/ai-suggestions${qs}`, { signal })
}

export function reviewAiSuggestion(
  suggestionId: number,
  payload: { status: ReviewAction; reviewed_by?: number | null; reason?: string | null },
): Promise<AiSuggestion> {
  return aitdeV2.post(`/ai-suggestions/${suggestionId}/review`, payload)
}

// ── Scenario gap ──

export function listScenarioGaps(missionId: number, signal?: AbortSignal): Promise<ScenarioGap[]> {
  return aitdeV2.get(`/missions/${missionId}/scenario-gaps`, { signal })
}

export function convertScenarioGap(
  gapId: number,
  payload: { title?: string | null; risk_level?: string; description?: string | null },
): Promise<{ gap_id: number; converted: boolean; title: string; risk_level: string; note: string }> {
  return aitdeV2.post(`/scenario-gaps/${gapId}/convert`, payload)
}

// ── Feedback ──

export function addFeedback(
  payload: {
    project_id?: number
    mission_id?: number | null
    target_type: string
    target_id: number
    feedback_type?: string
    before?: Record<string, unknown> | null
    after?: Record<string, unknown> | null
    reason?: string | null
  },
): Promise<HumanFeedback> {
  return aitdeV2.post('/feedback', payload)
}

export function listFeedback(targetType?: string | null, signal?: AbortSignal): Promise<HumanFeedback[]> {
  const qs = targetType ? `?target_type=${targetType}` : ''
  return aitdeV2.get(`/feedback${qs}`, { signal })
}

// ── Model evaluation ──

export function createModelEvaluation(
  payload: {
    evaluation_suite: string
    model_ref: string
    prompt_versions?: string[]
    metrics?: Record<string, unknown>
    status?: string
    artifact_uri?: string | null
  },
): Promise<ModelEvaluation> {
  return aitdeV2.post('/model-evaluations', payload)
}

export function listModelEvaluations(signal?: AbortSignal): Promise<ModelEvaluation[]> {
  return aitdeV2.get('/model-evaluations', { signal })
}

export function modelEvalRegressionCheck(evaluation_suite: string): Promise<{ ok: boolean; passed: boolean; score: number; threshold: number; reason: string }> {
  return aitdeV2.get(`/model-evaluations/regression-check?evaluation_suite=${encodeURIComponent(evaluation_suite)}`)
}

// ── Label maps ──

export const HYPOTHESIS_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  GENERATED: { label: '自动生成', color: 'bg-status-info-muted text-status-info' },
  REVIEWED: { label: '已复核', color: 'bg-status-warning-muted text-status-warning' },
  CONFIRMED: { label: '已确认', color: 'bg-status-success-muted text-status-success' },
  REJECTED: { label: '已拒绝', color: 'bg-muted text-muted-foreground' },
}

export const SUGGESTION_TYPE_LABELS: Record<string, string> = {
  HEALING: '愈合修复',
  DATA_STRATEGY: '数据策略',
  SCENARIO_GAP: '场景缺口',
  RISK: '风险',
  TRIAGE: '失败归因',
}

export const SUGGESTION_STATUS_LABELS: Record<string, string> = {
  OPEN: '待处理',
  APPROVED: '已批准',
  REJECTED: '已拒绝',
  APPLIED: '已应用',
  EXPIRED: '已过期',
}

export const GAP_TYPE_LABELS: Record<string, string> = {
  PROD_NEW_STATE: '生产新状态',
  HISTORICAL_DEFECT: '历史缺陷',
  REPEATED_BUSINESS_FAIL: '重复业务失败',
  UNCOVERED_CONTRACT_RULE: '未覆盖契约规则',
  UNCOVERED_JOURNEY: '未覆盖旅程',
  NEW_OPENAPI_STATE: '新 OpenAPI 状态',
}
