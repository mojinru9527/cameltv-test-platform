import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MissionContractPage from '../contract'

const mocks = vi.hoisted(() => ({
  fetchMissionAmbiguities: vi.fn(),
  fetchCurrentContract: vi.fn(),
}))

vi.mock('@/api/ambiguities', () => ({
  analyzeMissionAmbiguities: vi.fn(),
  fetchMissionAmbiguities: mocks.fetchMissionAmbiguities,
  resolveAmbiguity: vi.fn(),
  AMBIGUITY_STATUS_LABELS: {},
}))

vi.mock('@/api/contract', () => ({
  generateContract: vi.fn(),
  fetchCurrentContract: mocks.fetchCurrentContract,
  freezeContract: vi.fn(),
  CONTRACT_STATUS_LABELS: {
    FROZEN: { label: '已冻结', color: '' },
  },
}))

describe('MissionContractPage', () => {
  beforeEach(() => {
    mocks.fetchMissionAmbiguities.mockReset()
    mocks.fetchCurrentContract.mockReset()
    mocks.fetchMissionAmbiguities.mockResolvedValue([])
    mocks.fetchCurrentContract.mockResolvedValue({
      contract_id: 2,
      name: '体育 16.0.0 Contract',
      version_no: 2,
      version: {
        id: 2,
        contract_id: 2,
        version_no: 2,
        status: 'FROZEN',
        content_hash: 'hash',
        created_at: null,
        approved_at: null,
      },
    })
  })

  it('loads contract and ambiguity collections once on mount', async () => {
    render(
      <MemoryRouter initialEntries={['/missions/3/contract']}>
        <Routes>
          <Route path="/missions/:id/contract" element={<MissionContractPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('v2')
    await waitFor(() => {
      expect(mocks.fetchMissionAmbiguities).toHaveBeenCalledTimes(1)
      expect(mocks.fetchCurrentContract).toHaveBeenCalledTimes(1)
    })
    expect(mocks.fetchMissionAmbiguities.mock.calls[0][0]).toBe(3)
    expect(mocks.fetchCurrentContract.mock.calls[0][0]).toBe(3)
  })
})
