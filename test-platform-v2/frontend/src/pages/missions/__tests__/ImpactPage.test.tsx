import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  analyzeImpact: vi.fn(),
  fetchMissionImpactRuns: vi.fn(),
}))

vi.mock('@/api/smartRegression', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/smartRegression')>()
  return {
    ...original,
    analyzeImpact: mocks.analyzeImpact,
    fetchMissionImpactRuns: mocks.fetchMissionImpactRuns,
  }
})

import MissionImpactPage from '../impact'

describe('Mission impact initial state', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads the latest persisted impact run without starting a new analysis', async () => {
    mocks.fetchMissionImpactRuns.mockResolvedValue({
      items: [
        {
          id: 91,
          mission_id: 34,
          change_set_id: 71,
          algorithm_version: 'v1',
          status: 'COMPLETED',
          finished_at: '2026-09-07T10:05:00Z',
          results: [
            {
              id: 101,
              scenario_id: 501,
              scenario_version_id: 502,
              impact_score: 0.92,
              risk_level: 'P1',
              reasons: ['需求新增篮球多项目切换'],
              paths: [],
              decision: 'SELECTED',
            },
          ],
          unknown_changes: [],
        },
      ],
    })

    render(
      <MemoryRouter initialEntries={['/missions/34/impact']}>
        <Routes>
          <Route path="/missions/:id/impact" element={<MissionImpactPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('影响分析 #91')).toBeTruthy()
    expect(screen.getByText('已完成')).toBeTruthy()
    expect(screen.queryByText('COMPLETED')).toBeNull()
    expect(screen.getByText('Scenario #501')).toBeTruthy()
    expect(screen.getByText('需求新增篮球多项目切换')).toBeTruthy()
    await waitFor(() => expect(mocks.fetchMissionImpactRuns).toHaveBeenCalledTimes(1))
    expect(mocks.analyzeImpact).not.toHaveBeenCalled()
  })
})
