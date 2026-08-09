import client from './client'
import type { LoginResult, MeResult, MenuItem, Project, PublicAccessConfig } from '@/types'

export function login(username: string, password: string) {
  return client.post<unknown, LoginResult>('/auth/login', { username, password })
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
  return client.post<unknown, LoginResult>('/auth/register', body)
}

/** 未登录访客可读取的安全入口配置与模块目录。 */
export function fetchPublicAccess(signal?: AbortSignal) {
  if (signal) return client.get<unknown, PublicAccessConfig>('/auth/public-access', { signal })
  return client.get<unknown, PublicAccessConfig>('/auth/public-access')
}

/** P1-1: 通知后端清除 httpOnly 鉴权 cookie。 */
export function logoutApi() {
  return client.post<unknown, null>('/auth/logout')
}

export function fetchMe() {
  return client.get<unknown, MeResult>('/auth/me')
}

export function fetchMenus(signal?: AbortSignal) {
  if (signal) return client.get<unknown, MenuItem[]>('/system/menus', { signal })
  return client.get<unknown, MenuItem[]>('/system/menus')
}

export function fetchProjects() {
  return client.get<unknown, Project[]>('/projects')
}
