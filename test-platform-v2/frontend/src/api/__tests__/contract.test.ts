/**
 * Contract API tests — DEF-20260905-001.
 *
 * `fetchCurrentContract` must separate「尚未生成」(404 → null) from真实失败
 * (reject)，否则页面会把加载失败伪装成空数据（UI Red Flag #4）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockGet = vi.fn()

vi.mock('@/api/missions', () => ({
  aitdeV2: {
    get: (...args: any[]) => mockGet(...args),
    post: vi.fn(),
  },
}))

const { fetchCurrentContract } = await import('../contract')

describe('fetchCurrentContract', () => {
  beforeEach(() => {
    mockGet.mockReset()
  })

  it('hits the mission contract endpoint', async () => {
    mockGet.mockResolvedValue({ contract_id: 2, version_no: 1, version: null })

    await fetchCurrentContract(37)

    expect(mockGet).toHaveBeenCalledWith('/missions/37/contract', { signal: undefined })
  })

  it('resolves null when the envelope reports 404 (contract not generated yet)', async () => {
    mockGet.mockRejectedValue(Object.assign(new Error('Contract 尚未生成'), { code: 404 }))

    await expect(fetchCurrentContract(37)).resolves.toBeNull()
  })

  it('resolves null on HTTP 404', async () => {
    mockGet.mockRejectedValue({ response: { status: 404 }, message: 'Not Found' })

    await expect(fetchCurrentContract(37)).resolves.toBeNull()
  })

  it('rethrows non-404 failures so the page can render ErrorState', async () => {
    const serverError = Object.assign(new Error('服务器错误'), {
      response: { status: 500 },
    })
    mockGet.mockRejectedValue(serverError)

    await expect(fetchCurrentContract(37)).rejects.toBe(serverError)
  })

  it('rethrows abort errors rather than treating cancellation as "no contract"', async () => {
    const canceled = Object.assign(new Error('canceled'), { code: 'ERR_CANCELED' })
    mockGet.mockRejectedValue(canceled)

    await expect(fetchCurrentContract(37)).rejects.toBe(canceled)
  })
})
