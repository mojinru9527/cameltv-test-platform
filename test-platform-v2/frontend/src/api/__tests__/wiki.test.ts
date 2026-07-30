import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockGet = vi.fn()

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}))

const { fetchSyncCoverage } = await import('@/api/wiki')

describe('Wiki sync coverage API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads one release bundle coverage result with cancellation support', async () => {
    const controller = new AbortController()
    mockGet.mockResolvedValueOnce({
      total_pages: 4,
      synced_pages: 4,
      stale_pages: 0,
      missing_pages: 0,
      coverage_rate: 1,
    })

    await fetchSyncCoverage(17, controller.signal)

    expect(mockGet).toHaveBeenCalledWith(
      '/wiki/sync/bundle/17/coverage',
      { signal: controller.signal },
    )
  })
})
