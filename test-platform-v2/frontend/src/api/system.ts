import client from './client'
import { API_BASE_URL } from './baseUrl'
import { useAuthStore } from '@/stores/auth'

// ── 用户 ──
export function fetchUsers(signal?: AbortSignal) { return client.get('/system/users', { signal }) }
export function fetchUser(id: number) { return client.get(`/system/users/${id}`) }
export function createUser(body: any) { return client.post('/system/users', body) }
export function updateUser(id: number, body: any) { return client.put(`/system/users/${id}`, body) }
export function deleteUser(id: number) { return client.delete(`/system/users/${id}`) }

// ── 角色 ──
export function fetchRoles() { return client.get('/system/roles') }
export function createRole(body: any) { return client.post('/system/roles', body) }
export function updateRole(id: number, body: any) { return client.put(`/system/roles/${id}`, body) }
export function deleteRole(id: number) { return client.delete(`/system/roles/${id}`) }

// ── 权限 ──
export function fetchPermissions() { return client.get('/system/permissions') }

// ── 审计 ──
export function fetchAuditLogs(params?: any) { return client.get('/system/audit-logs', { params }) }

/** 导出审计日志 CSV，返回 Blob 供前端下载 */
export async function exportAuditLogsCsv(params?: { action?: string; keyword?: string }) {
  // Use fetch directly for binary download
  const { token, currentProjectId } = useAuthStore.getState()
  const searchParams = new URLSearchParams()
  if (params?.action) searchParams.set('action', params.action)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  const url = `${API_BASE_URL}/system/audit-logs/export?${searchParams.toString()}`
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  if (currentProjectId) headers['X-Project-Id'] = String(currentProjectId)
  const resp = await fetch(url, {
    credentials: 'include',
    headers,
  })
  if (!resp.ok) throw new Error('导出失败')
  const blob = await resp.blob()
  const contentDisposition = resp.headers.get('Content-Disposition') || ''
  const match = contentDisposition.match(/filename="?(.+?)"?$/)
  const filename = match?.[1] || 'audit-logs.csv'
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(a.href)
}
