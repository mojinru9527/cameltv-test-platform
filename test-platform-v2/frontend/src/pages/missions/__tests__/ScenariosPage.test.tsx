import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MissionScenariosPage from '../scenarios'

const mocks = vi.hoisted(() => ({
  fetchMissionScenarios: vi.fn(),
}))

vi.mock('@/api/scenarios', () => ({
  fetchMissionScenarios: (...args: unknown[]) => mocks.fetchMissionScenarios(...args),
  generateScenarios: vi.fn(),
  fetchScenario: vi.fn(),
  reviewScenario: vi.fn(),
  fetchFunctionalProjection: vi.fn(),
  SCENARIO_REVIEW_LABELS: {
    PROPOSED: { label: '待评审', color: '' },
  },
}))

vi.mock('@/api/contract', () => ({
  fetchCurrentContract: vi.fn(),
}))

vi.mock('@/config/aitde', () => ({
  useAitdeV3Enabled: () => true,
}))

describe('MissionScenariosPage', () => {
  beforeEach(() => {
    mocks.fetchMissionScenarios.mockReset()
    mocks.fetchMissionScenarios.mockResolvedValue([
      {
        id: 7,
        scenario_key: 'score-settlement-success',
        title: '比分结算成功',
        priority: 'P0',
        risk_level: 'HIGH',
        review_status: 'PROPOSED',
        version_no: 1,
        oracle_count: 2,
      },
    ])
  })

  it('loads scenarios once on mount and forwards an AbortSignal', async () => {
    render(
      <MemoryRouter initialEntries={['/missions/3/scenarios']}>
        <Routes>
          <Route path="/missions/:id/scenarios" element={<MissionScenariosPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('比分结算成功')
    await waitFor(() => expect(mocks.fetchMissionScenarios).toHaveBeenCalledTimes(1))
    expect(mocks.fetchMissionScenarios.mock.calls[0][0]).toBe(3)
    expect(mocks.fetchMissionScenarios.mock.calls[0][1]).toBeInstanceOf(AbortSignal)
  })
})
