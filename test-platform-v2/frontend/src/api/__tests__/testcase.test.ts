import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockDelete = vi.fn()
const mockPost = vi.fn()
const mockGet = vi.fn()

vi.mock('@/api/client', () => ({
  default: {
    delete: (...args: any[]) => mockDelete(...args),
    post: (...args: any[]) => mockPost(...args),
    get: (...args: any[]) => mockGet(...args),
  },
}))

const { createModule, deleteDomain, deleteModule, fetchTaxonomy, fetchTestCaseStats } = await import('@/api/testcase')

describe('test case category API calls', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls delete endpoint with the given domain id', async () => {
    mockDelete.mockResolvedValue({ data: {} })
    await deleteDomain(1)
    expect(mockDelete).toHaveBeenCalledWith('/test-cases/domains/1')
  })

  it('calls create endpoint with the given domain id and module name', async () => {
    mockPost.mockResolvedValue({ data: {} })
    await createModule(1, '登录模块')
    expect(mockPost).toHaveBeenCalledWith('/test-cases/domains/1/modules', { name: '登录模块' })
  })

  it('calls delete endpoint with the given domain and module id', async () => {
    mockDelete.mockResolvedValue({ data: {} })
    await deleteModule(1, 2)
    expect(mockDelete).toHaveBeenCalledWith('/test-cases/domains/1/modules/2')
  })

  it('loads authoritative case type statistics with an abort signal', async () => {
    const controller = new AbortController()
    mockGet.mockResolvedValue({ total: 4, by_type: { manual: 2, api: 1, ui: 1 } })

    const result = await fetchTestCaseStats(controller.signal)

    expect(mockGet).toHaveBeenCalledWith('/test-cases/stats', { signal: controller.signal })
    expect(result.by_type.manual).toBe(2)
  })

  it('loads the surface/domain/module taxonomy for the selected case type', async () => {
    const controller = new AbortController()
    mockGet.mockResolvedValue([])

    await fetchTaxonomy({ case_type: 'manual', surface: '用户端' }, controller.signal)

    expect(mockGet).toHaveBeenCalledWith('/test-cases/taxonomy', {
      params: { case_type: 'manual', surface: '用户端' },
      signal: controller.signal,
    })
  })
})
