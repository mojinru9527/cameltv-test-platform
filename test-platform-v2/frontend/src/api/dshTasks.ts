import api from './client'

// ── DSH 任务执行模块（Batch 172 / Batch 191 团队模式） ──

export interface DshTask {
  id: number
  project_id: number
  task: string
  status: string
  // Batch 191：'single' | 'team'
  mode: string
  // B1：场景标识（import_requirement/functional/api/ui/general）
  scene: string
  // Batch 191：团队进度快照（空 = {}；内容 = 插件 team.json 原文）
  team_json: Record<string, any>
  output_text: string
  session_dir: string
  error: string
  operator_id: number
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export interface DshTaskPage {
  items: DshTask[]
  total: number
  page: number
  page_size: number
}

export interface DshHealth {
  available: boolean
  reason: string
}

// DSH 测试 Agent 框架（阶段 3）：模型池
export interface DshModelPool {
  models: string[]
  default_model: string
  pool_configured: boolean
}

export interface DshTaskCreateResult extends DshTask {}

export async function fetchDshHealth(signal?: AbortSignal): Promise<DshHealth> {
  if (signal) return api.get('/dsh-tasks/health', { signal })
  return api.get('/dsh-tasks/health')
}

export async function fetchDshModelPool(signal?: AbortSignal): Promise<DshModelPool> {
  if (signal) return api.get('/dsh-tasks/model-pool', { signal })
  return api.get('/dsh-tasks/model-pool')
}

export async function fetchDshTasks(params: {
  status?: string
  page?: number
  page_size?: number
}, signal?: AbortSignal): Promise<DshTaskPage> {
  return api.get('/dsh-tasks', { params, ...(signal ? { signal } : {}) })
}

export async function fetchDshTask(id: number, signal?: AbortSignal): Promise<DshTask> {
  if (signal) return api.get(`/dsh-tasks/${id}`, { signal })
  return api.get(`/dsh-tasks/${id}`)
}

// Batch 191：mode='single'|'team'；团队模式必须带 params.batch_mode（full|light）
// B1：scene（import_requirement/functional/api/ui/general）+ scene_params 场景参数
export async function createDshTask(
  task: string,
  params?: Record<string, any>,
  mode?: 'single' | 'team',
  scene?: string,
  sceneParams?: Record<string, unknown>,
): Promise<DshTaskCreateResult> {
  return api.post('/dsh-tasks', {
    task,
    params: params ?? {},
    mode: mode ?? 'single',
    scene: scene ?? 'general',
    scene_params: sceneParams ?? {},
  })
}

export async function cancelDshTask(id: number): Promise<{ id: number; status: string; message: string }> {
  return api.post(`/dsh-tasks/${id}/cancel`)
}

// ── B2 产物闭环：任务产物回链 ──

export interface DshTaskArtifact {
  id: number
  artifact_type: string
  title: string
  review_status: string
  imported_ref_type: string
  imported_ref_id: number | null
}

export async function fetchDshTaskArtifacts(id: number, signal?: AbortSignal): Promise<DshTaskArtifact[]> {
  if (signal) return api.get(`/dsh-tasks/${id}/artifacts`, { signal })
  return api.get(`/dsh-tasks/${id}/artifacts`)
}
