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
    useAuthStore.setState({
      permissions: ['*'],
      projects: [{ id: 61, code: 'batch-61', name: 'Batch 61 安全项目' }],
      currentProjectId: 61,
    })
  })

  it('确认前不提交，确认后按当前页选中范围提交', async () => {
    render(<TestCasePage />)

    fireEvent.click(await screen.findByRole('checkbox', { name: '选择当前页全部用例' }))
    fireEvent.click(screen.getByRole('button', { name: '批量删除 (2)' }))

    expect(screen.getByRole('heading', { name: '确认批量删除用例？' })).toBeTruthy()
    expect(screen.getByText(/Batch 61 安全项目/)).toBeTruthy()
    expect(api.batchDeleteCases).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: '确认删除' }))

    await waitFor(() => expect(api.batchDeleteCases).toHaveBeenCalledWith([12, 11]))
  })

  it('取消批量删除时产生零写请求', async () => {
    render(<TestCasePage />)

    fireEvent.click(await screen.findByRole('checkbox', { name: '选择当前页全部用例' }))
    fireEvent.click(screen.getByRole('button', { name: '批量删除 (2)' }))
    fireEvent.click(screen.getByRole('button', { name: '取消' }))

    expect(api.batchDeleteCases).not.toHaveBeenCalled()
    expect(screen.queryByRole('heading', { name: '确认批量删除用例？' })).toBeNull()
  })

  it('快速重复确认只提交一次批量删除', async () => {
    let resolveDelete: (() => void) | undefined
    api.batchDeleteCases.mockImplementation(() => new Promise<void>((resolve) => {
      resolveDelete = resolve
    }))
    render(<TestCasePage />)

    fireEvent.click(await screen.findByRole('checkbox', { name: '选择当前页全部用例' }))
    fireEvent.click(screen.getByRole('button', { name: '批量删除 (2)' }))
    const confirm = screen.getByRole('button', { name: '确认删除' })
    fireEvent.click(confirm)
    fireEvent.click(confirm)

    expect(api.batchDeleteCases).toHaveBeenCalledTimes(1)
    resolveDelete?.()
    await waitFor(() => expect(screen.queryByRole('heading', { name: '确认批量删除用例？' })).toBeNull())
  })

  it('服务端原子失败时保留删除范围供复核', async () => {
    api.batchDeleteCases.mockRejectedValue(new Error('atomic rollback'))
    render(<TestCasePage />)

    fireEvent.click(await screen.findByRole('checkbox', { name: '选择当前页全部用例' }))
    fireEvent.click(screen.getByRole('button', { name: '批量删除 (2)' }))
    fireEvent.click(screen.getByRole('button', { name: '确认删除' }))

    await waitFor(() => expect(api.batchDeleteCases).toHaveBeenCalledTimes(1))
    expect(screen.getByRole('heading', { name: '确认批量删除用例？' })).toBeTruthy()
    expect(screen.getByText(/2 条用例/)).toBeTruthy()
  })
})
