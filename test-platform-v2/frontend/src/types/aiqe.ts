export interface AiqeRun {
  id: string
  run_key: string
  source_type: string
  status: string
  outcome: string | null
  workflow_definition_id?: string | null
  workflow_checksum?: string
  build_ref: string
  commit_sha: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
}

export interface AiqeAssertion {
  id: string
  assertion_key: string
  type: string
  status: string
  schema_version: string
  oracle_layer: string
  oracle_ref: string
  severity: string
  expected: unknown
  actual: unknown
  actual_source: string
  duration_ms: number
  timeout_ms: number
  error: string
  artifact_refs: string[]
}

export interface AiqeAttempt {
  id: string
  attempt_no: number
  status: string
  started_at: string | null
  finished_at: string | null
  error: Record<string, unknown> | null
  output: Record<string, unknown> | null
  assertions: AiqeAssertion[]
}

export interface AiqeNode {
  id: string
  node_key: string
  driver_key: string
  status: string
  error_class: string
  attempt_count: number
  inputs: Record<string, unknown>
  outputs: Record<string, unknown>
  secret_keys: string[]
  source_refs: Array<Record<string, unknown>>
  started_at: string | null
  finished_at: string | null
}

export interface AiqeRunNode {
  node: AiqeNode
  attempts: AiqeAttempt[]
  artifacts: AiqeRunArtifact[]
}

export interface AiqeRunNodes {
  run_id: string
  status: string
  outcome: string | null
  nodes: AiqeRunNode[]
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
