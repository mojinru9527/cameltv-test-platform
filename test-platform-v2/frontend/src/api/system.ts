import client from './client'

// ── 用户 ──
export function fetchUsers() { return client.get('/system/users') }
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
