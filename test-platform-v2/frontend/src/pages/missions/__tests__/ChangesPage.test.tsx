import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'

const fetchChangeSet = vi.fn()

vi.mock('@/api/smartRegression', () => ({
  CHANGE_KIND_LABELS: {},
  detectChanges: vi.fn(),
  fetchChangeSet: (...args: unknown[]) => fetchChangeSet(...args),
}))

import MissionChangesPage from '../changes'

describe('Mission changes initial state', () => {
  beforeEach(() => fetchChangeSet.mockReset())

  it('does not request a synthetic ChangeSet zero', async () => {
    render(
      <MemoryRouter initialEntries={['/missions/34/changes']}>
        <Routes>
          <Route path="/missions/:id/changes" element={<MissionChangesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('尚未发起检测。')).toBeTruthy()
    await waitFor(() => expect(fetchChangeSet).not.toHaveBeenCalled())
  })
})
