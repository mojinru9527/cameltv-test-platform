import api from './client'
import type { Environment, EnvironmentVariable } from '@/types'

const BASE = '/environments'

// ── Environment CRUD ──

export async function fetchEnvironments(): Promise<Environment[]> {
  return api.get(BASE)
}

export async function createEnvironment(body: {
  name: string; env_type?: string; base_url?: string; description?: string
}): Promise<Environment> {
  return api.post(BASE, body)
}

export async function updateEnvironment(id: number, body: {
  name?: string; env_type?: string; base_url?: string; description?: string
}): Promise<Environment> {
  return api.put(`${BASE}/${id}`, body)
}

export async function deleteEnvironment(id: number): Promise<{ deleted: boolean }> {
  return api.delete(`${BASE}/${id}`)
}

// ── Variable CRUD ──

export async function fetchVariables(envId: number): Promise<EnvironmentVariable[]> {
  return api.get(`${BASE}/${envId}/variables`)
}

export async function createVariable(envId: number, body: {
  key: string; value: string; encrypted?: boolean; description?: string
}): Promise<EnvironmentVariable> {
  return api.post(`${BASE}/${envId}/variables`, body)
}

export async function updateVariable(envId: number, varId: number, body: {
  key?: string; value?: string; encrypted?: boolean; description?: string
}): Promise<EnvironmentVariable> {
  return api.put(`${BASE}/${envId}/variables/${varId}`, body)
}

export async function deleteVariable(envId: number, varId: number): Promise<{ deleted: boolean }> {
  return api.delete(`${BASE}/${envId}/variables/${varId}`)
}

export async function resolveVariables(environmentId: number, template: string): Promise<{ resolved: string }> {
  return api.post(`${BASE}/resolve`, { environment_id: environmentId, template })
}
