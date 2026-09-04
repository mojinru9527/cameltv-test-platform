import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MissionScopePage from '../scope'

const mocks = vi.hoisted(() => ({
  fetchMissionScope: vi.fn(),
  reviewMissionScope: vi.fn(),
}))

vi.mock('@/api/scope', () => ({
  analyzeMissionScope: vi.fn(),
  fetchMissionScope: (...args: unknown[]) => mocks.fetchMissionScope(...args),
  reviewMissionScope: (...args: unknown[]) => mocks.reviewMissionScope(...args),
  DECISION_LABELS: {
    INCLUDE: { label: '纳入', color: '' },
  },
  REVIEW_LABELS: {
    PROPOSED: { label: '待评审', color: '' },
  },
  RISK_LABELS: { HIGH: '高' },
  SCOPE_TYPE_LABELS: { FEATURE: '功能' },
}))

describe('MissionScopePage', () => {
  beforeEach(() => {
    mocks.fetchMissionScope.mockReset()
    mocks.reviewMissionScope.mockReset()
    mocks.reviewMissionScope.mockResolvedValue({})
    mocks.fetchMissionScope.mockResolvedValue({
      items: [
        {
          id: 1,
          mission_id: 3,
          scope_key: 'score-settlement',
          scope_type: 'FEATURE',
          name: '比分结算',
          decision: 'INCLUDE',
          test_depth: 'DEEP',
          risk_level: 'HIGH',
          reason: '核心资金链路',
          ai_confidence: 0.95,
          review_status: 'PROPOSED',
          created_by_type: 'AI',
          created_at: null,
          updated_at: null,
        },
      ],
      summary: {
        total: 1,
        approved: 0,
        rejected: 0,
        proposed: 1,
        review_progress: 0,
        include_count: 1,
        exclude_count: 0,
      },
    })
  })

  it('loads the scope once on mount and forwards an AbortSignal', async () => {
    render(
      <MemoryRouter initialEntries={['/missions/3/scope']}>
        <Routes>
          <Route path="/missions/:id/scope" element={<MissionScopePage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('比分结算')
    await waitFor(() => expect(mocks.fetchMissionScope).toHaveBeenCalledTimes(1))
    expect(mocks.fetchMissionScope.mock.calls[0][0]).toBe(3)
    expect(mocks.fetchMissionScope.mock.calls[0][1]).toBeInstanceOf(AbortSignal)
  })

  it('refreshes the scope exactly once after a successful review', async () => {
    render(
      <MemoryRouter initialEntries={['/missions/3/scope']}>
        <Routes>
          <Route path="/missions/:id/scope" element={<MissionScopePage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('比分结算')
    fireEvent.click(screen.getByRole('button', { name: '批准 比分结算' }))

    await waitFor(() => expect(mocks.reviewMissionScope).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(mocks.fetchMissionScope).toHaveBeenCalledTimes(2))
  })
})
