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

function result(overrides: Record<string, unknown> = {}) {
  return {
    id: 'snap-1',
    gate_status: 'PASS',
    p0_total: 3,
    p0_passed: 3,
    p0_failed: 0,
    p0_blocked: 0,
    source_ids: ['run-1'],
    rule_version: 'v1.4-facts',
    reasons: [],
    immutable: true,
    ...overrides,
  }
}

describe('质量门禁页面（v1.4 facts-only）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('只提交 run_ids，展示 BLOCKED 与原因', async () => {
    api.evaluateQualityGate.mockResolvedValue(
      result({
        gate_status: 'BLOCKED',
        p0_total: 2,
        p0_passed: 1,
        p0_blocked: 1,
        reasons: ['1 条 P0 断言为 BLOCKED/ERROR/NOT_EVALUATED'],
      }),
    )

    renderPage()
    fireEvent.change(screen.getByLabelText('Run IDs'), {
      target: { value: 'run-1, run-2' },
    })
    fireEvent.click(screen.getByRole('button', { name: '判定门禁' }))

    const box = await screen.findByTestId('quality-gate-result')
    expect(within(box).getByText('BLOCKED')).toBeTruthy()
    expect(
      within(box).getByText('1 条 P0 断言为 BLOCKED/ERROR/NOT_EVALUATED'),
    ).toBeTruthy()
    expect(api.evaluateQualityGate).toHaveBeenCalledWith({
      run_ids: ['run-1', 'run-2'],
      version_task_id: undefined,
      build_ref: '',
      environment_ref: '',
    })
  })

  it('没有 Run/VersionTask 时不发请求', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: '判定门禁' }))
    expect(api.evaluateQualityGate).not.toHaveBeenCalled()
    expect(await screen.findByText(/必须提供 Run IDs 或 VersionTask ID/)).toBeTruthy()
  })

  it('P0 全通过 → PASS 且无原因列表', async () => {
    api.evaluateQualityGate.mockResolvedValue(result())

    renderPage()
    fireEvent.change(screen.getByLabelText('VersionTask ID'), {
      target: { value: '42' },
    })
    fireEvent.click(screen.getByRole('button', { name: '判定门禁' }))

    const box = await screen.findByTestId('quality-gate-result')
    expect(within(box).getByText('PASS')).toBeTruthy()
    expect(within(box).getByText('P0 全部通过')).toBeTruthy()
    expect(within(box).getByText(/v1.4-facts/)).toBeTruthy()
  })
})
