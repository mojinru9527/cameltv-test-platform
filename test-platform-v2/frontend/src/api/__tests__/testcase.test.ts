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

describe('test case category API guards', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not send a delete request when a domain id is missing', async () => {
    await expect(deleteDomain(undefined)).rejects.toThrow('分类接口尚未更新')
    expect(mockDelete).not.toHaveBeenCalled()
  })

  it('does not send a create-module request when a domain id is invalid', async () => {
    await expect(createModule(Number.NaN, '登录模块')).rejects.toThrow('分类接口尚未更新')
    expect(mockPost).not.toHaveBeenCalled()
  })

  it('does not send a delete request when a module id is missing', async () => {
    await expect(deleteModule(1, undefined)).rejects.toThrow('分类接口尚未更新')
    expect(mockDelete).not.toHaveBeenCalled()
  })
})
