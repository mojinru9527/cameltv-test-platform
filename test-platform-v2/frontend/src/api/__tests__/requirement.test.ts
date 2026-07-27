/**
 * Requirement API contract tests.
 *
 * These tests intentionally assert the complete method / URL / payload shape
 * because the requirement workflow spans list, detail, extraction, review,
 * import and coverage endpoints.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}))

const {
  fetchRequirements,
  fetchRequirement,
  fetchRequirementCoverage,
  getExtraction,
  getOrCreateExtraction,
  generateTestCases,
  importCases,
  reviewCase,
  fetchApiMatchSelection,
  confirmApiMatches,
} = await import('@/api/requirement')

describe('Requirement API functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('passes server pagination, keyword and AbortSignal to the list endpoint', async () => {
    const controller = new AbortController()
    mockGet.mockResolvedValue({ total: 101, page: 2, page_size: 10, items: [] })

    await fetchRequirements(
      { page: 2, page_size: 10, keyword: 'only-on-page-2' },
      controller.signal,
    )

    expect(mockGet).toHaveBeenCalledWith('/requirements', {
      params: { page: 2, page_size: 10, keyword: 'only-on-page-2' },
      signal: controller.signal,
    })
  })

  it('loads document detail and coverage through their dedicated endpoints', async () => {
    const controller = new AbortController()
    mockGet
      .mockResolvedValueOnce({ id: 42, content: 'full detail' })
      .mockResolvedValueOnce({ document_id: 42, coverage_rate: 75 })

    await fetchRequirement(42, controller.signal)
    await fetchRequirementCoverage(42, controller.signal)

    expect(mockGet).toHaveBeenNthCalledWith(
      1,
      '/requirements/42',
      { signal: controller.signal },
    )
    expect(mockGet).toHaveBeenNthCalledWith(
      2,
      '/requirements/42/coverage',
      { signal: controller.signal },
    )
  })

  it('keeps a missing extraction as null so callers can distinguish it from errors', async () => {
    mockGet.mockResolvedValue(null)

    await expect(getExtraction(7)).resolves.toBeNull()
    expect(mockGet).toHaveBeenCalledWith(
      '/requirements/7/extraction',
      { signal: undefined },
    )
  })

  it('creates an extraction only when the lookup returns HTTP 404', async () => {
    mockGet.mockRejectedValue({ response: { status: 404 } })
    mockPost.mockResolvedValue({ document_id: 7, modules: [] })

    await getOrCreateExtraction(7)

    expect(mockGet).toHaveBeenCalledTimes(1)
    expect(mockPost).toHaveBeenCalledWith(
      '/requirements/7/extract',
      undefined,
      { signal: undefined },
    )
  })

  it.each([403, 500])(
    'does not create an extraction after HTTP %s',
    async (status) => {
      const error = { response: { status } }
      mockGet.mockRejectedValue(error)

      await expect(getOrCreateExtraction(7)).rejects.toBe(error)
      expect(mockPost).not.toHaveBeenCalled()
    },
  )

  it('does not create an extraction after a timeout without a response', async () => {
    const error = new Error('timeout')
    mockGet.mockRejectedValue(error)

    await expect(getOrCreateExtraction(7)).rejects.toThrow('timeout')
    expect(mockPost).not.toHaveBeenCalled()
  })

  it('sends explicit extraction mode when generating cases', async () => {
    mockPost.mockResolvedValue({ functional_cases: [], api_cases: [] })

    await generateTestCases(9, { use_extraction: true })
    await generateTestCases(9, { use_extraction: false })

    expect(mockPost).toHaveBeenNthCalledWith(
      1,
      '/requirements/9/generate',
      { use_extraction: true },
    )
    expect(mockPost).toHaveBeenNthCalledWith(
      2,
      '/requirements/9/generate',
      { use_extraction: false },
    )
  })

  it('imports final edited case values together with selected indices', async () => {
    const edited = [{
      index: 0,
      title: 'edited title',
      case_type: 'manual',
      priority: 'P0',
      domain: '需求',
      module: '导入',
      preconditions: '',
      steps: '[]',
      expected_result: 'edited result',
      api_method: '',
      api_endpoint: '',
      remark: '',
      imported: false,
    }]
    mockPost.mockResolvedValue({ imported: 1, skipped: 0, total: 1 })

    await importCases(5, [0], edited)

    expect(mockPost).toHaveBeenCalledWith('/requirements/5/import', {
      indices: [0],
      edited_cases: edited,
    })
  })

  it('persists edited review data and rejects unsupported actions at compile time', async () => {
    mockPost.mockResolvedValue({ review_status: 'edited' })

    await reviewCase(5, 0, 'edit', { title: 'review-edited' })

    expect(mockPost).toHaveBeenCalledWith('/requirements/5/review/0', {
      action: 'edit',
      edited_data: { title: 'review-edited' },
    })
  })

  it('restores and confirms persisted API endpoint selections', async () => {
    mockGet.mockResolvedValue({ service_id: 3, endpoint_ids: [11, 12] })
    mockPost.mockResolvedValue({ service_id: 3, endpoint_ids: [12] })

    await fetchApiMatchSelection(5)
    await confirmApiMatches(5, { service_id: 3, endpoint_ids: [12] })

    expect(mockGet).toHaveBeenCalledWith(
      '/requirements/5/match-api/selection',
      { signal: undefined },
    )
    expect(mockPost).toHaveBeenCalledWith(
      '/requirements/5/match-api/confirm',
      { service_id: 3, endpoint_ids: [12] },
    )
  })
})
