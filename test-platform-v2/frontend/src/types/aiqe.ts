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
}

export interface AiqeRunPage {
  items: AiqeRun[]
  total: number
}
