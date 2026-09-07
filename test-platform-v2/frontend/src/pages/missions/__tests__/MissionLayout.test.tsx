import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  fetchMission: vi.fn(),
  fetchMissionLifecycle: vi.fn(),
}))

vi.mock('@/api/missions', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/missions')>()
  return {
    ...original,
    fetchMission: mocks.fetchMission,
    fetchMissionLifecycle: mocks.fetchMissionLifecycle,
  }
})

import MissionLayout from '../MissionLayout'

describe('MissionLayout acceptance status', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.fetchMission.mockResolvedValue({
      id: 34,
      mission_key: 'M-1-0034',
      mission_type: 'FEATURE',
      title: '体育平台 16.0.0 篮球多项目适配',
      version_label: '16.0.0',
      status: 'SCENARIO_READY',
      acceptance_status: 'PASS',
    })
    mocks.fetchMissionLifecycle.mockResolvedValue({
      mission: {
        id: 34,
        mission_type: 'FEATURE',
        status: 'SCENARIO_READY',
        acceptance_status: 'NOT_EVALUATED',
        stored_acceptance_status: 'PASS',
        acceptance_consistent: false,
        version_task_id: 6,
      },
      integrity_status: 'INCOMPLETE',
    })
  })

  it('ignores a stale stored PASS when supporting quality-gate facts are missing', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/missions/34/overview']}>
          <Routes>
            <Route path="/missions/:id" element={<MissionLayout />}>
              <Route path="overview" element={<div>概览内容</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByText('未验收')).toBeTruthy()
    expect(screen.queryByText('验收通过')).toBeNull()
    expect(screen.getByText(/已忽略与 Quality Gate 不一致的历史验收状态/)).toBeTruthy()
  })
})
