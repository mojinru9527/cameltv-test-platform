import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'

const fetchMissionChangeSets = vi.fn()

vi.mock('@/api/smartRegression', async (loadOriginal) => {
  const original = await loadOriginal<typeof import('@/api/smartRegression')>()
  return {
    ...original,
    fetchMissionChangeSets: (...args: unknown[]) => fetchMissionChangeSets(...args),
  }
})

import MissionChangesPage from '../changes'

describe('Mission changes initial state', () => {
  beforeEach(() => {
    fetchMissionChangeSets.mockReset()
    fetchMissionChangeSets.mockResolvedValue({ items: [] })
  })

  it('loads persisted mission change sets without creating example data', async () => {
    render(
      <MemoryRouter initialEntries={['/missions/34/changes']}>
        <Routes>
          <Route path="/missions/:id/changes" element={<MissionChangesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('尚无持久化的变化检测结果。')).toBeTruthy()
    await waitFor(() => expect(fetchMissionChangeSets).toHaveBeenCalledTimes(1))
    expect(fetchMissionChangeSets.mock.calls[0][0]).toBe(34)
    expect(fetchMissionChangeSets.mock.calls[0][1]).toBeInstanceOf(AbortSignal)
    expect(screen.queryByText('示例 PRD Diff')).toBeNull()
  })

  it('renders the persisted change items returned for the mission', async () => {
    fetchMissionChangeSets.mockResolvedValue({
      items: [
        {
          id: 71,
          mission_id: 34,
          change_type: 'REQUIREMENT',
          status: 'COMPLETED',
          content_hash: '1234567890abcdef1234567890abcdef',
          created_at: '2026-09-07T10:00:00Z',
          items: [
            {
              id: 81,
              change_kind: 'ADDED',
              entity_type: 'requirement',
              entity_key: '篮球多项目切换',
              risk_hint: 'P1',
            },
          ],
        },
      ],
    })

    render(
      <MemoryRouter initialEntries={['/missions/34/changes']}>
        <Routes>
          <Route path="/missions/:id/changes" element={<MissionChangesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('篮球多项目切换')).toBeTruthy()
    expect(screen.getByText('需求')).toBeTruthy()
    expect(screen.getByText('已完成')).toBeTruthy()
    expect(screen.getByText('变化记录 #71')).toBeTruthy()
    expect(screen.queryByText('COMPLETED')).toBeNull()
    expect(screen.getByText('P1')).toBeTruthy()
    expect(fetchMissionChangeSets).toHaveBeenCalledTimes(1)
  })
})
