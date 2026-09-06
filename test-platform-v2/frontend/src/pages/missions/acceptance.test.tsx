import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  fetchMissionAcceptance: vi.fn(),
  fetchMissionBuilds: vi.fn(),
  fetchMissionCampaigns: vi.fn(),
  evaluateGate: vi.fn(),
}))

vi.mock('@/api/continuous', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/continuous')>()
  return {
    ...original,
    fetchMissionAcceptance: mocks.fetchMissionAcceptance,
    fetchMissionBuilds: mocks.fetchMissionBuilds,
    fetchMissionCampaigns: mocks.fetchMissionCampaigns,
    evaluateGate: mocks.evaluateGate,
  }
})

import MissionAcceptancePage, { resolveGateCheckStatus } from './acceptance'

beforeEach(() => {
  vi.clearAllMocks()
  mocks.fetchMissionAcceptance.mockResolvedValue({ items: [] })
  mocks.fetchMissionBuilds.mockResolvedValue({ items: [] })
  mocks.fetchMissionCampaigns.mockResolvedValue({ items: [] })
})

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/missions/34/acceptance']}>
      <Routes>
        <Route path="/missions/:id/acceptance" element={<MissionAcceptancePage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Mission Gate evidence requirements', () => {
  it('disables evaluation until a real Build and Campaign are selected', async () => {
    renderPage()

    const button = await screen.findByRole('button', { name: '评估 Gate' })
    expect((button as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText('请选择 Build 和 Campaign 后再评估。')).toBeTruthy()
  })

  it('does not render historical zero-denominator PASS as PASS', () => {
    expect(resolveGateCheckStatus(
      { gate: 'G6_P0_BUSINESS_FAIL_ZERO', pass: true, detail: 'p0_business_fail=0' },
      { campaign_id: null, build_observation_id: null },
    )).toBe('NOT_EVALUATED')
    expect(resolveGateCheckStatus(
      { gate: 'G10_RUN_CONTRACT_MATCHES_FROZEN', pass: true, detail: 'contract_match=0/0 frozen=6' },
      { campaign_id: 1, build_observation_id: 1 },
    )).toBe('NOT_EVALUATED')
  })
})
