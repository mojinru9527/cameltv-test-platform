import client from './client'

// ── API Token（C63-1 / batch-70）──
export function fetchTokens(signal?: AbortSignal) {
  return client.get('/tokens', { signal })
}

export function createToken(body: { name: string; scopes?: string[] }) {
  return client.post('/tokens', body)
}

export function updateToken(id: number, body: { enabled?: boolean; name?: string; scopes?: string[] }) {
  return client.put(`/tokens/${id}`, body)
}

export function deleteToken(id: number) {
  return client.delete(`/tokens/${id}`)
}
