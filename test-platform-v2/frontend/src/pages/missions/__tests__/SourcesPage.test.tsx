import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MissionSourcesPage from '../sources'

const { fetchMissionSources } = vi.hoisted(() => ({
  fetchMissionSources: vi.fn(),
}))

vi.mock('@/api/sources', () => ({
  fetchMissionSources,
  fetchSourceFragments: vi.fn(),
  attachMissionSource: vi.fn(),
  parseMissionSource: vi.fn(),
  PARSE_STATUS_LABELS: {
    PARSED: { label: '已解析', color: '' },
  },
  SOURCE_TYPE_LABELS: {
    REQUIREMENT: '需求文档',
  },
}))

describe('MissionSourcesPage', () => {
  beforeEach(() => {
    fetchMissionSources.mockReset()
    fetchMissionSources.mockResolvedValue([
      {
        id: 1,
        name: '体育 16.0.0 需求',
        source_type: 'REQUIREMENT',
        parse_status: 'PARSED',
        fragment_count: 2,
      },
    ])
  })

  it('loads the source list once on mount', async () => {
    render(
      <MemoryRouter initialEntries={['/missions/3/sources']}>
        <Routes>
          <Route path="/missions/:id/sources" element={<MissionSourcesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('体育 16.0.0 需求')
    await waitFor(() => expect(fetchMissionSources).toHaveBeenCalledTimes(1))
    expect(fetchMissionSources.mock.calls[0][0]).toBe(3)
    expect(fetchMissionSources.mock.calls[0][1]).toBeInstanceOf(AbortSignal)
  })
})
