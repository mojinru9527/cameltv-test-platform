import { aitdeV2 } from './missions'

/** AIOperationRecord as exposed by GET /api/v2/ai-operations (V30-084/085). */
export interface AiOperation {
  id: number
  project_id: number
  mission_id: number
  operation_type: string
  status: string
  model_provider: string
  model_name: string
  prompt_version: string
  schema_version: string
  result_ref_json: string
  error_code: string
  error_message: string
  duration_ms: number
  token_usage_json: string
  created_at: string | null
  finished_at: string | null
}

/**
 * List a mission's AI operation records (AI Debug Drawer feed, V30-085).
 * Requires the `mission:ai_view_debug` permission.
 */
export function fetchAiOperations(missionId: number, signal?: AbortSignal): Promise<AiOperation[]> {
  return aitdeV2
    .get('/ai-operations', { params: { mission_id: missionId }, signal })
    .then((res) => (res as { items?: AiOperation[] } | undefined)?.items ?? [])
}

export const AI_OPERATION_STATUS_LABELS: Record<string, string> = {
  QUEUED: '排队中',
  RUNNING: '执行中',
  SUCCEEDED: '成功',
  FAILED: '失败',
  CANCELLED: '已取消',
}
