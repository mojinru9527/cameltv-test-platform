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
}

export interface AiqeRunPage {
  items: AiqeRun[]
  total: number
}
