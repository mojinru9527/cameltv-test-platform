import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMissionBuilds = vi.fn()

vi.mock('@/api/continuous', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/continuous')>()
  return { ...original, fetchMissionBuilds: (...args: unknown[]) => fetchMissionBuilds(...args) }
})

import MissionBuildsPage from './builds'

describe('Mission Build facts', () => {
  beforeEach(() => {
    fetchMissionBuilds.mockReset()
    fetchMissionBuilds.mockResolvedValue({
      items: [{
        id: 1,
        mission_id: 9101,
        environment_id: 1,
        fingerprint_id: 7,
        previous_fingerprint_id: null,
        change_summary_json: JSON.stringify({
          version: '16.0.0',
          target: 'https://camel-bball-test5.elelive.cn/basketball',
        }),
        detected_at: '2026-09-07T10:00:00Z',
        status: 'EVALUATED',
      }],
    })
  })

  it('renders the persisted version and target instead of presenting an id as a hash', async () => {
    render(
      <MemoryRouter initialEntries={['/missions/9101/builds']}>
        <Routes>
          <Route path="/missions/:id/builds" element={<MissionBuildsPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('16.0.0')).toBeTruthy()
    expect(screen.getByText('https://camel-bball-test5.elelive.cn/basketball')).toBeTruthy()
    expect(screen.getByText('已评估')).toBeTruthy()
    expect(screen.queryByText('指纹 Hash')).toBeNull()
  })
})
