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
  extraction_status?: string  // not_started | pending_review | confirmed
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
  extraction_status?: string
  version_info?: VersionInfo[]   // parsed version info from changelog
  client_summary?: string        // e.g. "涉及 App端、PC端"
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
