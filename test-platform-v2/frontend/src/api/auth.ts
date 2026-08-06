import client from './client'
import type { LoginResult, MeResult, MenuItem, Project } from '@/types'

export function login(username: string, password: string) {
  return client.post<unknown, LoginResult>('/auth/login', { username, password })
}

export interface RegisterPayload {
  username: string
  nickname?: string
  email?: string
  password: string
  invite_code?: string
}

/** Batch 104：开放注册（邀请码），成功后自动登录并写入 httpOnly cookie。 */
export function register(body: RegisterPayload) {
  return client.post<unknown, LoginResult>('/auth/register', body)
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
