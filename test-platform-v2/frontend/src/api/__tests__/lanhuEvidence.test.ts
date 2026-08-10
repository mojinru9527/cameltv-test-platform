import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockGet = vi.fn()

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}))

const {
  downloadLanhuEvidenceAsset,
  fetchLanhuEvidenceJobs,
} = await import('@/api/lanhuEvidence')

describe('Lanhu evidence API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('downloads the asset from the canonical route without a /download suffix', async () => {
    mockGet.mockResolvedValue(new Blob())

    await downloadLanhuEvidenceAsset(17)

    expect(mockGet).toHaveBeenCalledWith(
      '/lanhu-evidence/assets/17',
      { responseType: 'blob', signal: undefined, suppressErrorToast: true },
    )
  })

  it('supports abortable silent polling requests', async () => {
    const controller = new AbortController()
    mockGet.mockResolvedValue({ total: 0, items: [] })

    await fetchLanhuEvidenceJobs(
      { page: 1, page_size: 50 },
      controller.signal,
      true,
    )

    expect(mockGet).toHaveBeenCalledWith('/lanhu-evidence/jobs', {
      params: { page: 1, page_size: 50 },
      signal: controller.signal,
      suppressErrorToast: true,
    })
  })
})
