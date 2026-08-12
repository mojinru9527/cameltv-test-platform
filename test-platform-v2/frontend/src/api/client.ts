import { toast } from 'sonner'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { API_BASE_URL } from './baseUrl'

/** 统一返回体 { code, msg, data }。 */
interface ApiEnvelope<T> {
  code: number
  msg: string
  data: T
}

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000,
  withCredentials: true, // P1-1: 携带 httpOnly 鉴权 cookie
})

// 请求拦截：注入当前项目；JWT 由 httpOnly cookie 自动携带
// （过渡期：若内存中仍持有 token 则附加 Authorization 头作为兼容回退）
client.interceptors.request.use((config) => {
  const { token, currentProjectId } = useAuthStore.getState()
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (currentProjectId) config.headers['X-Project-Id'] = String(currentProjectId)
  return config
})

// 响应拦截：拆 envelope + 统一错误处理
client.interceptors.response.use(
  (resp) => {
    const body = resp.data as ApiEnvelope<unknown>
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) {
        // 业务错误不在此 toast，由调用方组件按需提示；
        // Batch 160：错误对象附带 envelope code，供调用方区分业务 404（HTTP 200 + code=404）等场景
        const businessError = new Error(body.msg) as Error & { code?: number }
        businessError.code = body.code
        return Promise.reject(businessError)
      }
      return body.data
    }
    return resp.data
  },
  (err) => {
    // Route changes and superseded queries intentionally abort Axios
    // requests. They are lifecycle events, not user-facing failures.
    if (axios.isCancel(err) || err.code === 'ERR_CANCELED') {
      return Promise.reject(err)
    }
    const status = err.response?.status
    const detail = err.response?.data?.detail
    let msg = err.response?.data?.msg || ''
    // FastAPI 422 的 detail 是对象数组，直接透传会被 toast 当作 React child 渲染而整页崩溃。
    // 统一转成可读字符串，字段名 + 原因，如「请求参数校验失败：assignee_id: Input should be a valid integer」。
    if (!msg && Array.isArray(detail)) {
      const parts = detail
        .map((d: any) => {
          const field = Array.isArray(d?.loc) && d.loc.length > 0 ? String(d.loc[d.loc.length - 1]) : ''
          return [field, d?.msg].filter(Boolean).join(': ')
        })
        .filter(Boolean)
      if (parts.length > 0) msg = `请求参数校验失败：${parts.join('; ')}`
    }
    msg = msg || (typeof detail === 'string' ? detail : '') || err.message || '网络错误'
    // Keep inline error states as specific as the toast. Axios otherwise
    // exposes only "Request failed with status code …" to page-level recovery UI.
    err.message = msg
    const suppressErrorToast = Boolean(
      (err.config as { suppressErrorToast?: boolean } | undefined)?.suppressErrorToast,
    )
    if (status === 401) {
      clearApiCache() // 会话失效，清空会话级缓存
      useAuthStore.getState().logout()
      if (location.pathname !== '/login') location.href = '/login'
    } else if (!suppressErrorToast) {
      toast.error(msg)
    }
    return Promise.reject(err)
  },
)

export default client

// ── 会话级 GET 缓存 + 进行中请求去重（Batch 150 / C147-5） ──

interface CacheEntry<T = unknown> {
  expires: number
  value: T
}

const getCache = new Map<string, CacheEntry>()
const inflightGets = new Map<string, Promise<unknown>>()

function cacheKey(url: string, params?: Record<string, unknown>): string {
  return `${url}?${JSON.stringify(params ?? {})}`
}

/**
 * 带会话级缓存与去重的 GET。
 * - 命中未过期缓存直接返回；相同 key 的进行中请求共享同一 Promise。
 * - 传 signal 时请直接使用 client.get，保持 abort 语义（本函数不接收 signal）。
 */
export function cachedGet<T>(
  url: string,
  params?: Record<string, unknown>,
  options?: { ttl?: number; force?: boolean },
): Promise<T> {
  const key = cacheKey(url, params)
  const now = Date.now()
  const ttl = options?.ttl ?? 60_000

  const hit = getCache.get(key)
  if (!options?.force && hit && hit.expires > now) {
    return Promise.resolve(hit.value as T)
  }

  const inflight = inflightGets.get(key)
  if (inflight) return inflight as Promise<T>

  const promise = client
    .get(url, { params })
    .then((data) => {
      getCache.set(key, { expires: Date.now() + ttl, value: data })
      return data
    })
    .finally(() => {
      inflightGets.delete(key)
    })
  inflightGets.set(key, promise)
  return promise as Promise<T>
}

/** 清空会话级缓存；传 prefix 只清理以该前缀开头的 key（如 '/environments'）。 */
export function clearApiCache(prefix?: string): void {
  if (!prefix) {
    getCache.clear()
    return
  }
  for (const key of [...getCache.keys()]) {
    if (key.startsWith(prefix)) getCache.delete(key)
  }
}
