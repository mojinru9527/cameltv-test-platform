const DEFAULT_API_BASE = '/api/v1'

export function resolveApiBase(value?: string): string {
  const configuredBase = value?.trim()
  if (!configuredBase) return DEFAULT_API_BASE
  return configuredBase.replace(/\/+$/, '')
}

export const API_BASE_URL = resolveApiBase(import.meta.env.VITE_API_BASE)
