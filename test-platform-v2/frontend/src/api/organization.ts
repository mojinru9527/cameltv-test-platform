import client from './client'
import type { Organization } from '@/types'

// ── 组织（Batch 105 租户模式）──

export interface OrganizationMember {
  organization_id: number
  user_id: number
  role_id: number
  username: string
  nickname: string
}

export interface OrgProject {
  id: number
  code: string
  name: string
  description: string
  status: number
  owner_id: number
}

export function fetchOrganizations(signal?: AbortSignal) {
  return client.get<unknown, Organization[]>('/organizations', { signal })
}

export function createOrganization(body: { code: string; name: string; description?: string }) {
  return client.post<unknown, Organization>('/organizations', body)
}

export function updateOrganization(id: number, body: { name?: string; description?: string; status?: number }) {
  return client.put<unknown, Organization>(`/organizations/${id}`, body)
}

export function disableOrganization(id: number) {
  return client.delete<unknown, { disabled: boolean }>(`/organizations/${id}`)
}

export function fetchOrgMembers(id: number) {
  return client.get<unknown, OrganizationMember[]>(`/organizations/${id}/members`)
}

export function addOrgMember(
  id: number,
  body: { username?: string; user_id?: number; role_id: number },
) {
  return client.post<unknown, OrganizationMember>(`/organizations/${id}/members`, body)
}

export function removeOrgMember(id: number, userId: number) {
  return client.delete(`/organizations/${id}/members/${userId}`)
}

export function fetchOrgProjects(id: number) {
  return client.get<unknown, OrgProject[]>(`/organizations/${id}/projects`)
}
