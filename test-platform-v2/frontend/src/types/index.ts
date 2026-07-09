/**
 * 业务类型（P0 手写）。
 * 后续可用 `npm run gen:api` 从后端 OpenAPI 自动生成 src/types/api.d.ts 替代。
 */
export interface User {
  id: number
  username: string
  nickname: string
  email: string
}

export interface Project {
  id: number
  code: string
  name: string
  description?: string
  status?: number
}

export interface LoginResult {
  access_token: string
  token_type: string
  user: User
  projects: Project[]
  permissions: string[]
}

export interface MeResult {
  user: User
  projects: Project[]
  permissions: string[]
  current_project_id: number | null
}

export interface MenuItem {
  code: string
  name: string
  path: string
  icon: string
  sort: number
  children?: MenuItem[]
}

// ========== P4: Dashboard / Report / Schedule ==========

export interface CaseTypeStat {
  case_type: string
  label: string
  color: string
  count: number
  execution_total: number
  execution_pass: number
  execution_fail: number
  pass_rate: number
  fail_rate: number
}

export interface CaseTypePriority {
  case_type: string
  label: string
  color: string
  p0: number
  p1: number
  p2: number
  p3: number
  total: number
}

export interface DashboardStats {
  total_cases: number
  total_plans: number
  api_cases: number
  pass_rate: number
  case_type_stats: CaseTypeStat[]
  priority_distribution: CaseTypePriority[]
  time_range: { start: string | null; end: string | null } | null
}

// ========== 需求文档 ==========

export interface RequirementDocument {
  id: number
  project_id: number
  creator_id: number
  creator_name: string
  title: string
  file_type: string
  source_ref: string
  content: string
  status: string
  extraction_status?: string  // not_started | extracting | pending_review | confirmed
  extraction_progress?: number  // V2: 0.0 - 1.0
  imported_count: number
  imported_func_count: number
  imported_api_count: number
  parsed_type: string
  excel_cases: Record<string, string>[]
  created_at: string | null
}

export interface AIGeneratedCase {
  index: number
  title: string
  case_type: string     // "manual"
  priority: string      // "P0" | "P1" | "P2" | "P3"
  domain: string
  module: string
  preconditions: string
  steps: string          // JSON string
  expected_result: string
  api_method: string
  api_endpoint: string
  remark: string
  imported: boolean      // whether this case has been imported
  client_scope?: string[]  // ["app", "pc", "web"] — applicable client platforms
}

// Requirement Analysis (two-phase AI output)
export interface Issue {
  severity: string       // "high" | "medium" | "low"
  description: string
  suggestion: string
}

export interface ExtractedRequirement {
  id: string             // "REQ-1"
  title: string
  description: string
  type: string           // "functional" | "ui" | "data" | "integration"
  issues: Issue[]
}

export interface RequirementAnalysis {
  extracted_requirements: ExtractedRequirement[]
  overall_assessment: string
}

export interface AIGenerateResult {
  document_id: number
  requirement_analysis?: RequirementAnalysis | null
  functional_cases: AIGeneratedCase[]
  api_cases?: AIGeneratedCase[]    // deprecated — always empty
  raw_response: string
  extraction_summary?: string      // Lanhu extraction status info
}

// ── Stage 1: Feature Extraction ──

export interface TestFunctionPoint {
  id: string              // "FP-1"
  title: string
  description: string
  type: string            // "functional" | "ui" | "data" | "integration"
  client_scope: string[]  // ["app", "pc", "web"] — applicable client platforms
  issues: Issue[]
}

export interface VersionInfo {
  version: string
  title: string
  update_items: string[]
  clients: string[]
  folder_hint: string
}

export interface TestModule {
  id: string              // "MOD-1"
  name: string
  description: string
  function_points: TestFunctionPoint[]
}

export interface FeatureExtractionResult {
  document_id: number
  modules: TestModule[]
  overall_assessment: string
  raw_response: string
  extraction_summary?: string
  extraction_status?: string       // not_started | extracting | pending_review | confirmed
  version_info?: VersionInfo[]     // parsed version info from changelog
  client_summary?: string          // e.g. "涉及 App端、PC端"
  // V2 enhanced extraction
  truncated?: boolean              // True if extraction was cut off
  extraction_progress?: number     // 0.0-1.0
  versions_total?: number          // Total versions from changelog
  versions_done?: number           // Versions fully extracted
}

export interface ExtractionConfirmRequest {
  action: 'confirm' | 'reject'
  modules?: TestModule[]
  rejected_modules?: string[]
  rejected_notes?: string
}

export interface ReportItem {
  id: number
  report_id: string
  name: string
  description: string
  plan_id: number
  plan_name: string
  creator_id: number
  created_at: string | null
  updated_at: string | null
}

export interface ScheduleItem {
  id: number
  name: string
  description: string
  plan_id: number
  plan_name: string
  cron_expression: string
  enabled: boolean
  next_run: string | null
  last_run: string | null
  created_at: string | null
}

export interface ScheduleRunItem {
  id: number
  schedule_id: number
  status: string
  result: Record<string, number> | null
  error_message: string
  started_at: string | null
  finished_at: string | null
}

// ========== P5: Defect / AV / UI ==========

export interface DefectItem {
  id: number
  defect_id: string
  title: string
  description: string
  severity: string
  status: string
  case_id: number | null
  execution_id: number | null
  assignee_id: number
  assignee_name: string
  external_id: string
  external_url: string
  creator_id: number
  creator_name: string
  case_title: string
  resolved_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface AvTaskItem {
  id: number
  task_id: string
  name: string
  stream_url: string
  protocol: string
  status: string
  last_result: string
  creator_id: number
  creator_name: string
  metrics: AvMetricItem[]
  created_at: string | null
  updated_at: string | null
}

export interface AvMetricItem {
  id: number
  task_id: number
  metric_name: string
  metric_value: number
  threshold: number
  pass_: boolean
  detail: string
}

export interface UiJobItem {
  id: number
  name: string
  description: string
  test_spec: string
  browser: string
  status: string
  last_result: Record<string, any> | null
  creator_id: number
  creator_name: string
  last_run_status: string
  last_run_time: string | null
  created_at: string | null
  updated_at: string | null
}

export interface UiRunItem {
  id: number
  job_id: number
  status: string
  result: Record<string, any> | null
  screenshots: string[]
  video_url: string
  trace_id: string
  started_at: string | null
  finished_at: string | null
}

export interface DefectTransition {
  id: number
  defect_id: number
  from_status: string
  to_status: string
  comment?: string
  operator_id?: number
  operator_name?: string
  created_at: string
}

export interface DefectComment {
  id: number
  defect_id: number
  content: string
  author_id?: number
  author_name?: string
  created_at: string
}

export interface DefectAttachment {
  id: number
  defect_id: number
  filename: string
  file_size: number
  mime_type?: string
  uploader_name?: string
  created_at: string
}

export interface ProjectDetail {
  id: number
  code: string
  name: string
  description: string
  owner_id: number
  config: string
  status: number
  created_at: string | null
  updated_at: string | null
}

// ── Environment & Variables ──

export interface Environment {
  id: number
  project_id: number
  name: string
  env_type: string           // dev | test | staging | prod
  base_url: string
  description: string
  created_at: string | null
  updated_at: string | null
}

export interface EnvironmentVariable {
  id: number
  environment_id: number
  key: string
  value: string
  encrypted: boolean
  description: string
  created_at: string | null
  updated_at: string | null
}

// ── TestCase Version ──

export interface TestCaseVersion {
  id: number
  case_id: number
  version_number: number
  changed_by: number
  changed_fields: string[]
  created_at: string | null
}

export interface TestCaseVersionDetail extends TestCaseVersion {
  snapshot: Record<string, any>
}

// ── API Test Execution ──

export interface ApiAssertion {
  type: string           // "status_code" | "jsonpath" | "regex" | "response_time"
  path?: string          // JSONPath or field
  expected: any
  operator: string       // "eq" | "neq" | "gt" | "lt" | "contains" | "exists" | "regex"
  pattern?: string       // for regex type
}

export interface ApiExecutionResult {
  status: string
  status_code: number
  response_headers: Record<string, string>
  response_body: any
  duration_ms: number
  assertions: ApiAssertionResult[]
  all_pass: boolean
  error?: string
  executed_at?: string
}

export interface ApiAssertionResult {
  type: string
  expected: any
  actual: any
  passed: boolean
  message: string
}

export interface QuickExecuteRequest {
  method: string
  url: string
  headers: string       // JSON string
  body: string          // JSON string
  assertions?: string
  environment_id?: number
  dataset_id?: number
  service_name?: string  // for asset debug: service name for URL composition
  query_params?: string  // JSON string of query key-value pairs
}

// ── Dataset (V2.5) ──

export interface Dataset {
  id: number
  project_id: number
  name: string
  description: string
  source_type: 'csv' | 'json' | 'sql'
  raw_content: string
  sql_query: string
  connection_string: string
  row_count: number
  columns_meta: string     // JSON string: ["col1", "col2", ...]
  created_at: string | null
  updated_at: string | null
}

export interface DatasetListItem {
  id: number
  project_id: number
  name: string
  description: string
  source_type: string
  row_count: number
  columns_meta: string
  created_at: string | null
  updated_at: string | null
}

export interface DatasetPreview {
  columns: string[]
  rows: Record<string, string>[]
  total_rows: number
}

export interface DatasetUploadResponse {
  dataset: Dataset
  preview: DatasetPreview
}

export interface BatchExecutionResult {
  status: string
  batch_mode: boolean
  dataset_id: number
  columns: string[]
  total_rows: number
  passed: number
  failed: number
  per_row: Array<{
    row_index: number
    row_data: Record<string, string>
    result: ApiExecutionResult
  }>
  executed_at: string
}

// ── Cross-Project Dashboard (V2.5) ──

export interface CrossProjectCard {
  project_id: number
  project_name: string
  total_cases: number
  total_plans: number
  api_cases: number
  pass_rate: number
  defect_count: number
}

export interface CrossProjectAggregate {
  total_projects: number
  total_cases: number
  total_plans: number
  total_api_cases: number
  overall_pass_rate: number
  total_defects: number
}

export interface TrendPoint {
  date: string
  pass_rate?: number
  total_execs?: number
  count?: number
}

export interface CrossProjectTrends {
  pass_rate: TrendPoint[]
  defects: TrendPoint[]
}

export interface CrossProjectStats {
  projects: Array<{ id: number; code: string; name: string }>
  aggregate: CrossProjectAggregate
  per_project: CrossProjectCard[]
  trends: CrossProjectTrends
}

// ── TestCase Review ──

export interface TestCaseReviewTransition {
  id: number
  case_id: number
  from_status: string
  from_label: string
  to_status: string
  to_label: string
  comment: string
  reviewer_id: number
  reviewer_name: string
  created_at: string | null
}

// ── Quality Gate ──

export interface QualityGateConfig {
  project_id: number
  pass_rate_threshold: number
  p0_max: number
  p1_max: number
  enabled: boolean
  is_default?: boolean
}

// ── Integration Config (V2.6) ──

export interface IntegrationConfig {
  id: number
  project_id: number
  name: string
  provider_type: 'jira' | 'tapd'
  base_url: string
  auth_json: string       // always "********" in response
  field_mapping: string    // JSON string
  sync_direction: string   // bidirectional | push_only | pull_only
  sync_interval_minutes: number
  enabled: boolean
  created_at: string | null
  updated_at: string | null
}

export interface SyncLog {
  id: number
  integration_id: number
  defect_id: number
  direction: 'push' | 'pull'
  status: 'success' | 'failed' | 'skipped'
  external_id: string
  message: string
  created_at: string | null
}

export interface TestConnectionResult {
  success: boolean
  message: string
}

// ── API Test Asset Types (接口测试模块优化) ──

export interface ApiService {
  id: number
  project_id: number
  name: string
  display_name: string
  description: string
  default_base_path: string
  owner: string
  status: string
  endpoint_count: number
  created_at: string | null
  updated_at: string | null
}

export interface ApiEndpoint {
  id: number
  project_id: number
  service_id: number
  module: string
  method: string
  path: string
  summary: string
  description: string
  request_schema: string
  response_schema: string
  auth_required: boolean
  deprecated: boolean
  source: string
  import_batch_id: number | null
  version: string
  created_at: string | null
  updated_at: string | null
}

export interface ApiImportPreview {
  service_name: string
  version: string
  total_count: number
  new_count: number
  existing_count: number
  doc_url: string
  spec_urls: string[]
  discovered_by: string
  modules: Array<{ name: string; count: number }>
  endpoints: Array<{
    module: string
    method: string
    path: string
    summary: string
    source: string
    _exists?: boolean
  }>
  errors: Array<{ method: string; path: string; error: string }>
}

export interface ApiImportResult {
  batch_id: number
  service_name: string
  version: string
  total_count: number
  created_count: number
  updated_count: number
  skipped_count: number
  generated_case_count: number
  errors: Array<{ method: string; path: string; error: string }>
}

export interface ApiExecutionTask {
  id: number
  project_id: number
  task_id: string
  name: string
  environment_id: number | null
  service_id: number | null
  status: string
  total: number
  passed: number
  failed: number
  skipped: number
  trigger_type: string
  creator_id: number
  started_at: string | null
  finished_at: string | null
  created_at: string | null
}

export interface ApiExecutionTaskItem {
  id: number
  task_id: number
  case_id: number
  status: string
  duration_ms: number
  request_snapshot: string
  response_snapshot: string
  assertion_results: string
  error_message: string
  created_at: string | null
}

export interface ApiTaskDetail extends ApiExecutionTask {
  items: ApiExecutionTaskItem[]
}

export interface GenerateApiCasesRequest {
  endpoint_id?: number
  endpoint_data?: Record<string, any>
  templates?: string[]
  import_to_case_library?: boolean
  module?: string
  service_name?: string
}

export interface BatchGenerateRequest {
  endpoint_ids: number[]
  templates?: string[]
  import_to_case_library?: boolean
}

export interface ApiTaskCreateRequest {
  name: string
  environment_id?: number
  service_id?: number
  case_ids: number[]
}

// ========== 知识中心 (RAG / Agent 持续学习) ==========

export interface KnowledgePage<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface KnowledgeSource {
  id: number
  project_id: number
  source_type: string
  source_id: number | null
  title: string
  source_ref: string
  version: string
  status: string
  created_at?: string
  // 详情附加字段
  content_hash?: string
  iteration_id?: number | null
  raw_content?: string
  metadata_json?: string
  updated_at?: string
}

export interface KnowledgeChunk {
  id: number
  project_id: number
  source_id: number
  chunk_type: string
  title: string
  content: string
  content_hash: string
  token_count: number
  embedding_id: string
  tags: string
  status: string
  created_at?: string
}

export interface AiArtifact {
  id: number
  project_id: number
  artifact_type: string
  title: string
  content_json: string
  source_refs: string
  agent_run_id: number | null
  confidence: number
  review_status: string
  reviewer_id: number
  review_comment: string
  imported_ref_type: string
  imported_ref_id: number | null
  created_at?: string
}

export interface KnowledgeHealth {
  unreviewed_artifacts: number
  deprecated_sources: number
  sourceless_chunks: number
  low_confidence_relations: number
}

export interface KnowledgeOverview {
  source_count: number
  chunk_count: number
  entity_count: number
  pending_artifact_count: number
  recent_sources: KnowledgeSource[]
  health: KnowledgeHealth
}
