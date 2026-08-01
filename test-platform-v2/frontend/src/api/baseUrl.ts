const DEFAULT_API_BASE = '/api/v1'

interface ApiBaseEnv {
  VITE_API_BASE_URL?: string
  VITE_API_BASE?: string
}

export function resolveApiBase(value?: string): string {
  const configuredBase = value?.trim()
  if (!configuredBase) return DEFAULT_API_BASE
  return configuredBase.replace(/\/+$/, '')
}

export function resolveApiBaseFromEnv(env: ApiBaseEnv): string {
  return resolveApiBase(env.VITE_API_BASE_URL?.trim() || env.VITE_API_BASE)
}

export const API_BASE_URL = resolveApiBaseFromEnv({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_API_BASE: import.meta.env.VITE_API_BASE,
})

export function resolveApiUrl(path: string, apiBase: string = API_BASE_URL): string {
  const resourcePath = path.replace(/^\/+/, '')
  return `${resolveApiBase(apiBase)}/${resourcePath}`
}
