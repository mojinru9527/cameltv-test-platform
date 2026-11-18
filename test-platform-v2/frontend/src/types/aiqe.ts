export interface AiqeRun {
  id: string
  run_key: string
  source_type: string
  status: string
  outcome: string | null
  build_ref: string
  commit_sha: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
}

export interface AiqeRunEvent {
  id: string
  seq: number
  event_type: string
  producer: string
  occurred_at: string
  payload_json: Record<string, unknown>
  node_run_id: string | null
  step_attempt_id: string | null
}

export interface AiqeRunArtifact {
  id: string
  artifact_type: string
  sha256: string
  size_bytes: number
  mime_type: string
  redaction_status: string
  created_at: string
  // AUD-008：上传生命周期与保留期（后端计算）
  content_type?: string
  upload_status?: 'PENDING_UPLOAD' | 'AVAILABLE' | 'CORRUPTED' | 'FAILED' | 'PURGED'
  retention_until?: string | null
  node_run_id?: string | null
}

export interface AiqeRunAssertion {
  id: string
  node_key: string
  attempt_no: number
  assertion_key: string
  assertion_type: string
  status: string
  required: boolean
  expected: unknown
  actual: unknown
  oracle_type: string | null
  oracle_id: string | null
  evaluator_version: string | null
  source_ref: string | null
  duration_ms: number | null
  evaluated_at: string | null
}

export interface AiqeRunPage {
  items: AiqeRun[]
  total: number
}
