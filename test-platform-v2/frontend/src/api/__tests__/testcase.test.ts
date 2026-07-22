import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockDelete = vi.fn()
const mockPost = vi.fn()

vi.mock('@/api/client', () => ({
  default: {
    delete: (...args: any[]) => mockDelete(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}))

const { createModule, deleteDomain, deleteModule } = await import('@/api/testcase')

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
})
