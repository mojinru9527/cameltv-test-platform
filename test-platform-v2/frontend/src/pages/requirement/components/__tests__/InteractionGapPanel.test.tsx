import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockGaps = vi.fn()

vi.mock('@/api/requirement', () => ({
  interactionCoverageGaps: (...a: unknown[]) => mockGaps(...a),
}))

const { default: InteractionGapPanel } = await import('../InteractionGapPanel')

afterEach(() => {
  cleanup()
  mockGaps.mockReset()
})

describe('InteractionGapPanel (C119-2)', () => {
  it('renders coverage summary and gap list', async () => {
    mockGaps.mockResolvedValue({
      total_edges: 8,
      covered_edges: 3,
      gap_edges: 5,
      coverage_rate: 0.375,
      gaps: [
        { from_module: '首页', entry: 'FIFA World Cup 2026', to: '/worldcup-2026' },
        { from_module: '首页', entry: 'Match ReplaysShow more', to: '/match-replay' },
      ],
    })
    render(<InteractionGapPanel />)
    await waitFor(() => expect(mockGaps).toHaveBeenCalledWith([], expect.any(AbortSignal)))
    expect(screen.getByText('覆盖率 37.5%')).toBeTruthy()
    expect(screen.getByText('已覆盖 3/8 边 · 缺口 5')).toBeTruthy()
    expect(screen.getAllByText('缺口').length).toBeGreaterThan(0)
    expect(screen.getByText(/worldcup-2026/)).toBeTruthy()
  })

  it('renders empty state when no gaps', async () => {
    mockGaps.mockResolvedValue({
      total_edges: 8,
      covered_edges: 8,
      gap_edges: 0,
      coverage_rate: 1,
      gaps: [],
    })
    render(<InteractionGapPanel />)
    await waitFor(() => expect(mockGaps).toHaveBeenCalledWith([], expect.any(AbortSignal)))
    expect(screen.getByText('暂无覆盖缺口')).toBeTruthy()
  })

  it('shows error and retry', async () => {
    mockGaps.mockRejectedValueOnce(new Error('接口失败')).mockResolvedValueOnce({
      total_edges: 1,
      covered_edges: 1,
      gap_edges: 0,
      coverage_rate: 1,
      gaps: [],
    })
    render(<InteractionGapPanel />)
    await waitFor(() => expect(screen.getByText('接口失败')).toBeTruthy())
  })

  it('supports filtering and paging through the complete gap set', async () => {
    mockGaps.mockResolvedValue({
      total_edges: 55,
      covered_edges: 0,
      gap_edges: 55,
      coverage_rate: 0,
      gaps: Array.from({ length: 55 }, (_, index) => ({
        from_module: index === 54 ? '搜索模块' : '首页',
        entry: `入口 ${index + 1}`,
        to: `/target-${index + 1}`,
      })),
    })
    render(<InteractionGapPanel />)

    expect(await screen.findByText(/target-1$/)).toBeTruthy()
    expect(screen.queryByText(/target-51$/)).toBeNull()
    expect(screen.getByText('第 1 / 2 页')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '下一页缺口' }))
    expect(await screen.findByText(/target-51$/)).toBeTruthy()

    fireEvent.change(screen.getByRole('searchbox', { name: '筛选交互缺口' }), {
      target: { value: '搜索模块' },
    })
    expect(screen.getByText(/target-55$/)).toBeTruthy()
    expect(screen.queryByText(/target-51$/)).toBeNull()
  })
})
