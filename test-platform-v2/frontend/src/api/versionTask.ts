import axios from 'axios'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth'

interface Envelope<T> {
  code: number
  msg: string
  data: T
}

const v1 = axios.create({
  baseURL: '/api/v1',
  timeout: 600000,
  withCredentials: true,
})
v1.interceptors.request.use((config) => {
  const { token, currentProjectId } = useAuthStore.getState()
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (currentProjectId) config.headers['X-Project-Id'] = String(currentProjectId)
  return config
})
v1.interceptors.response.use(
  (resp) => {
    const body = resp.data as Envelope<unknown>
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) {
        const businessError = new Error(body.msg) as Error & { code?: number }
        businessError.code = body.code
        return Promise.reject(businessError)
      }
      return body.data
    }
    return resp.data
  },
  (err) => {
    const status = err.response?.status
    const msg = err.response?.data?.msg || err.response?.data?.detail || err.message || '网络错误'
    err.message = msg
    if (status === 401) {
      useAuthStore.getState().logout()
      if (location.pathname !== '/login') location.href = '/login'
    } else {
      toast.error(msg)
    }
    return Promise.reject(err)
  },
)

export interface VersionTask {
  id: number
  project_id: number
  title: string
  version: string
  source: string
  status: string
  verdict: string
  requirement_doc_id?: number | null
  release_bundle_id?: number | null
  environment_id?: number | null
  scope: Record<string, unknown>
  summary: string
  coverage: Record<string, unknown>
  risk: Record<string, unknown>
  qa_owner_id: number
  created_at?: string
  updated_at?: string
}

export interface PlanItem {
  id: number
  item_type: string
  title: string
  description: string
  confidence: number
  status: string
  question: string
  answer: string
  order_index: number
}

export async function listVersionTasks(
  status = '',
  keyword = '',
): Promise<{ total: number; items: VersionTask[] }> {
  const p = new URLSearchParams()
  if (status) p.set('status', status)
  if (keyword) p.set('keyword', keyword)
  return (await v1.get(`/version-tasks?${p.toString()}`)) as unknown as { total: number; items: VersionTask[] }
}

export async function getVersionTask(id: number): Promise<VersionTask> {
  return (await v1.get(`/version-tasks/${id}`)) as unknown as VersionTask
}

export async function createVersionTask(body: Record<string, unknown>): Promise<VersionTask> {
  return (await v1.post('/version-tasks', body)) as unknown as VersionTask
}

export async function transitionVersionTask(
  id: number,
  status: string,
  verdict = '',
  summary = '',
): Promise<VersionTask> {
  return (await v1.post(`/version-tasks/${id}/transition`, { status, verdict, summary })) as unknown as VersionTask
}

export async function generatePlan(
  id: number,
  items: { item_type: string; title: string; description?: string; confidence?: number; question?: string }[],
): Promise<PlanItem[]> {
  return (await v1.post(`/version-tasks/${id}/plan/generate`, items)) as unknown as PlanItem[]
}

export async function reviewPlanItem(
  taskId: number,
  itemId: number,
  action: string,
  patch: Record<string, unknown> = {},
): Promise<PlanItem> {
  return (await v1.post(`/version-tasks/${taskId}/plan/${itemId}/review`, { action, ...patch })) as unknown as PlanItem
}

export async function getPlan(taskId: number): Promise<PlanItem[]> {
  return (await v1.get(`/version-tasks/${taskId}/plan`)) as unknown as PlanItem[]
}


export interface VersionTaskRun {
  id: number
  task_id: number
  status: string
  progress: number
  total: number
  passed: number
  failed: number
  skipped: number
  blocked: number
  evidence: { type: string; ref: string; url: string; ts: string; status: string }[]
  failures: { item_id: number; title: string; kind: string; evidence: string; message: string }[]
}

export async function startRun(taskId: number): Promise<VersionTaskRun> {
  return (await v1.post(`/version-tasks/${taskId}/run`)) as unknown as VersionTaskRun
}

export async function listRuns(taskId: number): Promise<VersionTaskRun[]> {
  return (await v1.get(`/version-tasks/${taskId}/runs`)) as unknown as VersionTaskRun[]
}

export async function createDefectDraft(taskId: number, runId: number, failureIndex: number): Promise<{ defect_id: number; status: string }> {
  return (await v1.post(`/version-tasks/${taskId}/runs/${runId}/defect/${failureIndex}`)) as unknown as { defect_id: number; status: string }
}


export interface ReleasePackage {
  task_id: number
  title: string
  version: string
  status: string
  verdict: string
  coverage: Record<string, number>
  pass_rate: number
  total_checks: number
  risk: string[]
  defects: { id: number; defect_id: number }[]
  release_bundle_id: number | null
  summary: string
}

export async function buildReleasePackage(taskId: number): Promise<ReleasePackage> {
  return (await v1.get(`/version-tasks/${taskId}/release-package`)) as unknown as ReleasePackage
}

export async function releaseTask(
  taskId: number,
  verdict: string,
  releaseBundleId?: number,
  risk: string[] = [],
  summary?: string,
): Promise<ReleasePackage> {
  return (await v1.post(`/version-tasks/${taskId}/release`, {
    verdict, release_bundle_id: releaseBundleId ?? null, risk, summary,
  })) as unknown as ReleasePackage
}

export async function notifyRelease(taskId: number): Promise<{ sent: boolean }> {
  return (await v1.post(`/version-tasks/${taskId}/notify`)) as unknown as { sent: boolean }
}


export interface RegressionItem {
  kind: string
  title: string
  source: string
  priority: string
}

export async function getRegressionSet(taskId: number): Promise<RegressionItem[]> {
  return (await v1.get(`/version-tasks/${taskId}/regression-set`)) as unknown as RegressionItem[]
}

export async function syncDefect(taskId: number, defectId: number): Promise<{ synced: boolean; defect_id: number }> {
  return (await v1.post(`/version-tasks/${taskId}/defects/${defectId}/sync`)) as unknown as { synced: boolean; defect_id: number }
}
