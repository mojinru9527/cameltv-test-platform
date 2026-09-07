import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  fetchMissionRuns: vi.fn(),
}))

vi.mock('@/api/executions', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/executions')>()
  return { ...original, fetchMissionRuns: mocks.fetchMissionRuns }
})

vi.mock('@/api/scenarios', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/scenarios')>()
  return { ...original, fetchMissionScenarios: vi.fn() }
})

vi.mock('@/api/contract', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/contract')>()
  return { ...original, fetchCurrentContract: vi.fn() }
})

vi.mock('@/api/environment', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/environment')>()
  return { ...original, fetchEnvironments: vi.fn() }
})

import MissionExecutionsPage from './mission'

describe('Mission execution facts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.fetchMissionRuns.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      items: [
        {
          id: 901,
          mission_id: 34,
          scenario_id: 501,
          scenario_version_id: 502,
          contract_version_id: 601,
          environment_id: 5,
          runtime_status: 'FINISHED',
          outcome: 'PASS',
          evidence_status: 'COMPLETE',
          trigger_type: 'MANUAL',
          retry_no: 0,
          created_by: 1,
          created_at: '2026-09-07T10:10:00Z',
          scenario_title: '篮球多项目切换 UI 验证',
          case_type: 'UI',
          requirement_role: 'NEW',
          step_count: 4,
          assertion_count: 3,
          evidence_count: 2,
          verified_evidence_count: 2,
          replay_available: true,
        },
      ],
    })
  })

  it('shows per-run result, evidence counts, and replay access', async () => {
    render(
      <MemoryRouter initialEntries={['/missions/34/executions']}>
        <Routes>
          <Route path="/missions/:id/executions" element={<MissionExecutionsPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('篮球多项目切换 UI 验证')).toBeTruthy()
    expect(screen.getByText('UI 自动化')).toBeTruthy()
    expect(screen.getByText('新增需求')).toBeTruthy()
    expect(screen.queryByText('NEW')).toBeNull()
    expect(screen.getByText((_, element) => (
      element?.tagName === 'TD'
      && element.textContent?.includes('步骤 4 · 断言 3') === true
      && element.textContent?.includes('已验证证据 2/2') === true
    ))).toBeTruthy()
    expect(screen.getByRole('button', { name: /回放 Run/ })).toBeTruthy()
  })
})
