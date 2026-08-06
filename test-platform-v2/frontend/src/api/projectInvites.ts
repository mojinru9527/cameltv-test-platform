import client from './client'

// ── 项目邀请链接（Batch 106）──

export interface ProjectInvite {
  id: number
  project_id: number
  token: string
  url?: string
  usage_limit: number
  used_count: number
  expires_at: string | null
  status: number
  created_at: string | null
}

export function fetchProjectInvites(projectId: number) {
  return client.get<unknown, ProjectInvite[]>(`/projects/${projectId}/invites`)
}

export function createProjectInvite(
  projectId: number,
  body: { usage_limit?: number; expires_at?: string | null },
) {
  return client.post<unknown, ProjectInvite>(`/projects/${projectId}/invites`, body)
}

export function disableProjectInvite(projectId: number, inviteId: number) {
  return client.post<unknown, { disabled: boolean }>(
    `/projects/${projectId}/invites/${inviteId}/disable`,
  )
}
