import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  addCasesToPlan: vi.fn(),
  fetchDomains: vi.fn(),
  fetchTestCases: vi.fn(),
}))

vi.mock('@/api/testplan', () => ({
  addCasesToPlan: mocks.addCasesToPlan,
}))

vi.mock('@/api/testcase', () => ({
  fetchDomains: mocks.fetchDomains,
  fetchTestCases: mocks.fetchTestCases,
}))

vi.mock('@/components/DomainTree', () => ({
  default: ({ onSelect }: { onSelect: (keys: string[]) => void }) => (
    <button type="button" onClick={() => onSelect(['交易域::支付模块'])}>
      选择支付模块
    </button>
  ),
}))

vi.mock('@/components/Pagination', () => ({
  default: () => null,
}))

import AddCasesModal from './AddCasesModal'

describe('AddCasesModal filters', () => {
  beforeEach(() => {
    mocks.addCasesToPlan.mockReset()
    mocks.fetchDomains.mockReset().mockResolvedValue([
      {
        domain: '交易域',
        count: 1,
        modules: [{ module: '支付模块', count: 1 }],
      },
    ])
    mocks.fetchTestCases.mockReset().mockResolvedValue({
      total: 0,
      items: [],
      page: 1,
      page_size: 10,
    })
  })

  it('uses the newly selected domain and module in the same request', async () => {
    render(
      <AddCasesModal
        open
        planId={59}
        onClose={vi.fn()}
        onAdded={vi.fn()}
      />,
    )

    await waitFor(() => expect(mocks.fetchTestCases).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('button', { name: '选择支付模块' }))

    await waitFor(() => {
      expect(mocks.fetchTestCases).toHaveBeenLastCalledWith(
        {
          page: 1,
          page_size: 10,
          domain: '交易域',
          module: '支付模块',
        },
        expect.any(AbortSignal),
      )
    })
  })

  it('applies the latest keyword when Enter is pressed', async () => {
    render(
      <AddCasesModal
        open
        planId={59}
        onClose={vi.fn()}
        onAdded={vi.fn()}
      />,
    )

    await waitFor(() => expect(mocks.fetchTestCases).toHaveBeenCalledTimes(1))
    const search = screen.getByPlaceholderText('搜索标题')
    fireEvent.change(search, { target: { value: '退款失败' } })
    fireEvent.keyDown(search, { key: 'Enter' })

    await waitFor(() => {
      expect(mocks.fetchTestCases).toHaveBeenLastCalledWith(
        {
          page: 1,
          page_size: 10,
          keyword: '退款失败',
        },
        expect.any(AbortSignal),
      )
    })
  })
})
