import api from './client'

export interface PlaygroundCompileResult {
  spec_code: string
  spec_type: string
  compile_ms: number
}

export interface PlaygroundExecuteResult {
  passed: boolean
  stdout: string
  stderr: string
  screenshot_base64?: string | null
  duration_ms: number
}

export async function compilePlayground(
  body: { source: string; source_type: string; case_id?: string },
  signal?: AbortSignal,
): Promise<PlaygroundCompileResult> {
  return api.post('/playground/compile', body, { ...(signal ? { signal } : {}) })
}

export async function executePlayground(
  body: { spec_code: string; timeout_ms?: number },
  signal?: AbortSignal,
): Promise<PlaygroundExecuteResult> {
  return api.post('/playground/execute', body, { ...(signal ? { signal } : {}) })
}

export interface PlaygroundCaseCompileItem {
  case_id: number
  case_title: string
  spec_code: string
  has_todo: boolean
}

export interface PlaygroundBatchCompileResult {
  total: number
  items: PlaygroundCaseCompileItem[]
}

export interface PlaygroundCaseRunResult {
  case_id: number
  case_title: string
  spec_code: string
  passed: boolean
  stdout: string
  stderr: string
  screenshot_base64?: string | null
  duration_ms: number
  ui_job_id?: number | null
  todo_blocked?: boolean
}

export interface PlaygroundBatchRunResult {
  total: number
  passed: number
  failed: number
  todo_blocked?: number
  results: PlaygroundCaseRunResult[]
  report: Record<string, any>
}

export async function compilePlaygroundBatch(
  body: { case_ids: number[] },
  signal?: AbortSignal,
): Promise<PlaygroundBatchCompileResult> {
  return api.post('/playground/batch-compile', body, { ...(signal ? { signal } : {}) })
}

export async function runPlaygroundBatch(
  body: { case_ids: number[]; write_back_to_ui?: boolean; timeout_ms?: number },
  signal?: AbortSignal,
): Promise<PlaygroundBatchRunResult> {
  return api.post('/playground/batch-run', body, { ...(signal ? { signal } : {}) })
}
