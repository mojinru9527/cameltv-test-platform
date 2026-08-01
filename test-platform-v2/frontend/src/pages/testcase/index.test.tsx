import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'

const api = vi.hoisted(() => ({
  batchDeleteCases: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/api/testcase', () => ({
  batchDeleteCases: (...args: unknown[]) => api.batchDeleteCases(...args),
  batchUpdateCases: vi.fn(),
  deleteTestCase: vi.fn(),
  fetchDomains: vi.fn(),
  fetchTestCases: vi.fn(),
  fetchVersions: vi.fn(),
  reviewCase: vi.fn(),
}))

vi.mock('@/hooks/useApi', () => ({
  useApi: (_fetcher: unknown, deps: unknown[]) => deps.length === 0
    ? { data: [], isLoading: false, isError: false, error: null, refetch: vi.fn() }
    : {
        data: {
          total: 2,
          page: 1,
          page_size: 20,
          items: [
            { id: 11, title: '体育接口用例 A', domain: '赛事', module: '直播', priority: 'P0', review_status: 'draft' },
            { id: 12, title: '体育接口用例 B', domain: '赛事', module: '直播', priority: 'P1', review_status: 'draft' },
          ],
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      },
}))

vi.mock('@/components/DomainTree', () => ({ default: () => <div /> }))
vi.mock('@/components/Pagination', () => ({ default: () => <div /> }))
vi.mock('./CaseDrawer', () => ({ default: () => null }))
vi.mock('./VersionDialog', () => ({ default: () => null }))

import TestCasePage from './index'

describe('用例批量删除确认', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.batchDeleteCases.mockResolvedValue({})
    useAuthStore.setState({ permissions: ['*'] })
  })

  it('确认前不提交，确认后按当前页选中范围提交', async () => {
    render(<TestCasePage />)

    fireEvent.click(await screen.findByRole('checkbox', { name: '选择当前页全部用例' }))
    fireEvent.click(screen.getByRole('button', { name: '批量删除 (2)' }))

    expect(screen.getByRole('heading', { name: '确认批量删除用例？' })).toBeTruthy()
    expect(api.batchDeleteCases).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: '确认删除' }))

    await waitFor(() => expect(api.batchDeleteCases).toHaveBeenCalledWith([12, 11]))
  })
})
