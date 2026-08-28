import axios from 'axios'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth'

/** AITDE v2 client — shares the platform's auth cookie + X-Project-Id header. */
interface Envelope<T> {
  code: number
  msg: string
  data: T
}

const v2 = axios.create({
  baseURL: '/api/v2',
  timeout: 600000,
  withCredentials: true,
})

v2.interceptors.request.use((config) => {
  const { token, currentProjectId } = useAuthStore.getState()
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (currentProjectId) config.headers['X-Project-Id'] = String(currentProjectId)
  return config
})

v2.interceptors.response.use(
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
    const msg =
      err.response?.data?.msg || err.response?.data?.detail || err.message || '网络错误'
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

// ── AITDE Mission domain types ──

export interface Mission {
  id: number
  project_id: number
  mission_key: string
  mission_type: 'VERSION' | 'FEATURE' | 'HOTFIX' | 'REGRESSION' | 'EXPLORATORY' | string
  title: string
  version_label: string | null
  status: string
  owner_id: number | null
  qa_owner_id: number | null
  default_environment_id: number | null
  current_contract_version_id: number | null
  acceptance_status: string
  legacy_version_mission_id: number | null
  created_by: number
  created_at: string | null
  updated_at: string | null
  archived_at: string | null
}

export interface MissionListResult {
  total: number
  page: number
  page_size: number
  items: Mission[]
}

export interface MissionCreateInput {
  title: string
  mission_type?: string
  version_label?: string | null
  qa_owner_id?: number | null
  default_environment_id?: number | null
}

export interface MissionUpdateInput {
  title?: string
  version_label?: string | null
  owner_id?: number | null
  qa_owner_id?: number | null
  default_environment_id?: number | null
  status?: string
  acceptance_status?: string
}

export interface MissionListParams {
  status?: string
  mission_type?: string
  keyword?: string
  page?: number
  page_size?: number
}

// ── AITDE Mission API ──

export function fetchMissions(
  params: MissionListParams = {},
  signal?: AbortSignal,
): Promise<MissionListResult> {
  return v2.get('/missions', { params, signal })
}

export function fetchMission(id: number, signal?: AbortSignal): Promise<Mission> {
  return v2.get(`/missions/${id}`, { signal })
}

export function createMission(payload: MissionCreateInput): Promise<Mission> {
  return v2.post('/missions', payload)
}

export function updateMission(id: number, payload: MissionUpdateInput): Promise<Mission> {
  return v2.patch(`/missions/${id}`, payload)
}

export function archiveMission(id: number): Promise<Mission> {
  return v2.post(`/missions/${id}/archive`)
}

// ── UI label/colour maps ──

export const MISSION_TYPE_LABELS: Record<string, string> = {
  VERSION: '版本测试',
  FEATURE: '功能测试',
  HOTFIX: 'Hotfix',
  REGRESSION: '回归',
  EXPLORATORY: '探索',
}

export const MISSION_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'bg-muted text-muted-foreground' },
  SOURCE_READY: { label: '资料就绪', color: 'bg-status-info-muted text-status-info' },
  SCOPE_ANALYZING: { label: '范围分析中', color: 'bg-status-info-muted text-status-info' },
  SCOPE_REVIEW: { label: '范围评审', color: 'bg-status-warning-muted text-status-warning' },
  CONTRACT_BUILDING: { label: '契约构建中', color: 'bg-status-info-muted text-status-info' },
  CONTRACT_REVIEW: { label: '契约评审', color: 'bg-status-warning-muted text-status-warning' },
  CONTRACT_FROZEN: { label: '契约已冻结', color: 'bg-status-success-muted text-status-success' },
  SCENARIO_BUILDING: { label: '场景构建中', color: 'bg-status-info-muted text-status-info' },
  SCENARIO_REVIEW: { label: '场景评审', color: 'bg-status-warning-muted text-status-warning' },
  SCENARIO_READY: { label: '场景就绪', color: 'bg-status-success-muted text-status-success' },
  ARCHIVED: { label: '已归档', color: 'bg-muted text-muted-foreground' },
}
