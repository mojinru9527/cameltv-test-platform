import client from './client'

// ── API Token（C63-1 / batch-70）──
export interface ApiTokenItem {
  id: number
  name: string
  token_prefix: string
  scopes: string[] | string
  enabled: boolean
  last_used_at: string | null
  created_at: string | null
}

export interface CreatedApiToken extends ApiTokenItem {
  token: string
}

export async function fetchTokens(signal?: AbortSignal): Promise<ApiTokenItem[]> {
  return client.get('/tokens', { signal })
}

export async function createToken(body: { name: string; scopes?: string[] }): Promise<CreatedApiToken> {
  return client.post('/tokens', body)
}

export function updateToken(id: number, body: { enabled?: boolean; name?: string; scopes?: string[] }) {
  return client.put(`/tokens/${id}`, body)
}

export function deleteToken(id: number) {
  return client.delete(`/tokens/${id}`)
}
