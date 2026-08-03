import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import client from '../client'
import { createToken, deleteToken, fetchTokens, updateToken } from '../token'

describe('token api client（batch-70）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchTokens → GET /tokens', () => {
    fetchTokens()
    expect(client.get).toHaveBeenCalledWith('/tokens', { signal: undefined })
  })

  it('createToken → POST /tokens', () => {
    createToken({ name: 'ci-token', scopes: ['trigger'] })
    expect(client.post).toHaveBeenCalledWith('/tokens', { name: 'ci-token', scopes: ['trigger'] })
  })

  it('updateToken → PUT /tokens/{id}', () => {
    updateToken(3, { enabled: false })
    expect(client.put).toHaveBeenCalledWith('/tokens/3', { enabled: false })
  })

  it('deleteToken → DELETE /tokens/{id}', () => {
    deleteToken(3)
    expect(client.delete).toHaveBeenCalledWith('/tokens/3')
  })
})
