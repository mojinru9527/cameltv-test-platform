import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ evaluateQualityGate: vi.fn() }))
vi.mock('@/api/aiqeConsole', () => ({ evaluateQualityGate: api.evaluateQualityGate }))

const { default: QualityGatePage } = await import('@/pages/aiqe/quality-gate')

function renderPage() {
  return render(
    <MemoryRouter>
      <QualityGatePage />
    </MemoryRouter>,
  )
}

describe('质量门禁页面（batch-338）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('P0 有未执行 → 展示 BLOCKED 与原因', async () => {
    api.evaluateQualityGate.mockResolvedValue({
      gate_status: 'BLOCKED',
      p0_total: 2,
      p0_passed: 1,
      p0_failed: 0,
      p0_unknown: 0,
      p0_not_run: 1,
      reasons: ['1 条 P0 未执行'],
    })

    renderPage()

    fireEvent.change(screen.getByLabelText('P0 总数'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('P0 通过'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('P0 未执行'), { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: '判定门禁' }))

    const result = await screen.findByTestId('quality-gate-result')
    expect(within(result).getByText('BLOCKED')).toBeTruthy()
    expect(within(result).getByText('1 条 P0 未执行')).toBeTruthy()
    expect(api.evaluateQualityGate).toHaveBeenCalledWith({
      p0_total: 2,
      p0_passed: 1,
      p0_failed: 0,
      p0_unknown: 0,
      p0_not_run: 1,
    })
  })

  it('P0 全通过 → PASS 且无原因列表', async () => {
    api.evaluateQualityGate.mockResolvedValue({
      gate_status: 'PASS',
      p0_total: 3,
      p0_passed: 3,
      p0_failed: 0,
      p0_unknown: 0,
      p0_not_run: 0,
      reasons: [],
    })

    renderPage()
    fireEvent.change(screen.getByLabelText('P0 总数'), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText('P0 通过'), { target: { value: '3' } })
    fireEvent.click(screen.getByRole('button', { name: '判定门禁' }))

    const result = await screen.findByTestId('quality-gate-result')
    expect(within(result).getByText('PASS')).toBeTruthy()
    expect(within(result).getByText('P0 全部通过')).toBeTruthy()
  })
})
