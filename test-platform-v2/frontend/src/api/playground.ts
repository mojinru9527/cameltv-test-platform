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
