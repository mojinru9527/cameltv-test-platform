import client, { cachedGet } from './client'
import type { MenuItem } from '@/types'
import type { LoginOut, PublicAccessOut } from './apiContract'

export function login(username: string, password: string) {
  return client.post<unknown, LoginOut>('/auth/login', { username, password })
}

export interface RegisterPayload {
  username: string
  nickname?: string
  email?: string
  password: string
  invite_code?: string
  project_invite_token?: string
}

/** 普通用户注册；受控环境可由后端策略要求平台邀请码。 */
export function register(body: RegisterPayload) {
  return client.post<unknown, LoginOut>('/auth/register', body)
}

/** 未登录访客可读取的安全入口配置与模块目录。 */
export function fetchPublicAccess(signal?: AbortSignal) {
  if (signal) return client.get<unknown, PublicAccessOut>('/auth/public-access', { signal })
  return client.get<unknown, PublicAccessOut>('/auth/public-access')
}

/** 请求密码重置邮件；后端采用防用户名枚举的统一响应。 */
export function forgotPassword(username: string) {
  return client.post<unknown, null>('/auth/forgot-password', { username })
}

/** 使用邮件中的一次性 token 设置新密码。 */
export function resetPassword(token: string, newPassword: string) {
  return client.post<unknown, null>('/auth/reset-password', {
    token,
    new_password: newPassword,
  })
}

/** P1-1: 通知后端清除 httpOnly 鉴权 cookie。 */
export function logoutApi() {
  return client.post<unknown, null>('/auth/logout')
}

export function fetchMenus(signal?: AbortSignal) {
  // Batch 150: 会话级缓存（TTL 60s）；Batch 176（FIX-173-P1-02）：传 signal 也命中缓存，
  // 整页刷新/路由重挂载不再重复请求静态菜单。
  return cachedGet<MenuItem[]>('/system/menus', undefined, { ttl: 60_000, signal })
}
