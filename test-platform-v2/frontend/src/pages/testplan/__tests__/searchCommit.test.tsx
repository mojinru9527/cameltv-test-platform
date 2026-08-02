import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  fetchPlans: vi.fn(),
  deletePlan: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/api/testplan', () => ({
  fetchPlans: (...args: unknown[]) => api.fetchPlans(...args),
  deletePlan: (...args: unknown[]) => api.deletePlan(...args),
}))

vi.mock('@/hooks/useDocumentTitle', () => ({
  useDocumentTitle: () => {},
}))

vi.mock('@/components/DataTable', () => ({
  default: ({ toolbar }: { toolbar?: React.ReactNode }) => (
    <div data-testid="plan-table">{toolbar}</div>
  ),
}))

vi.mock('@/components/state', () => ({
  AsyncState: ({ children }: { children: React.ReactNode | (() => React.ReactNode) }) => (
    <div>{typeof children === 'function' ? (children as () => React.ReactNode)() : children}</div>
  ),
}))

vi.mock('../PlanDrawer', () => ({ default: () => null }))

import TestPlanPage from '../index'

describe('测试计划搜索提交态（B60-P2-001）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.fetchPlans.mockResolvedValue({ total: 0, items: [], page: 1, page_size: 20 })
  })

  it('输入关键字不触发请求，仅提交（按钮/回车）触发一次有效 GET', async () => {
    render(
      <MemoryRouter>
        <TestPlanPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(api.fetchPlans).toHaveBeenCalledTimes(1))

    const input = await screen.findByRole('textbox')
    fireEvent.change(input, { target: { value: '赛事' } })
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(api.fetchPlans).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: '搜索' }))
    await waitFor(() => expect(api.fetchPlans).toHaveBeenCalledTimes(2))
    expect(api.fetchPlans).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 20,
      keyword: '赛事',
    })

    fireEvent.change(input, { target: { value: '赛事2' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(api.fetchPlans).toHaveBeenCalledTimes(3))
    expect(api.fetchPlans).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 20,
      keyword: '赛事2',
    })
  })
})
