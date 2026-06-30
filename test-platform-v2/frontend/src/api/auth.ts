import client from './client'
import type { LoginResult, MeResult, MenuItem, Project } from '@/types'

export function login(username: string, password: string) {
  return client.post<unknown, LoginResult>('/auth/login', { username, password })
}

export function fetchMe() {
  return client.get<unknown, MeResult>('/auth/me')
}

export function fetchMenus() {
  return client.get<unknown, MenuItem[]>('/system/menus')
}

export function fetchProjects() {
  return client.get<unknown, Project[]>('/projects')
}
