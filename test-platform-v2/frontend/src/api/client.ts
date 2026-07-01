import { toast } from 'sonner'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

/** 统一返回体 { code, msg, data }。 */
interface ApiEnvelope<T> {
  code: number
  msg: string
  data: T
}

const client = axios.create({
  baseURL: '/api/v1',
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
        toast.error(body.msg || '请求失败')
        return Promise.reject(new Error(body.msg))
      }
      return body.data
    }
    return resp.data
  },
  (err) => {
    const status = err.response?.status
    const msg = err.response?.data?.msg || err.message || '网络错误'
    if (status === 401) {
      useAuthStore.getState().logout()
      if (location.pathname !== '/login') location.href = '/login'
    } else {
      toast.error(msg)
    }
    return Promise.reject(err)
  },
)

export default client
