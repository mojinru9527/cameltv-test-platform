import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DefectPage from '../index'

const apiMocks = vi.hoisted(() => ({ fetchDefect: vi.fn() }))

vi.mock('@/api/defect', () => ({
  fetchDefect: apiMocks.fetchDefect,
  fetchDefects: vi.fn(),
  fetchDefectStats: vi.fn(),
}))

vi.mock('@/hooks/useApi', () => ({
  default: () => ({ data: undefined, isLoading: false, isError: false, error: null, refetch: vi.fn() }),
}))

vi.mock('../DefectStatsCards', () => ({ default: () => null }))
vi.mock('../DefectFilterBar', () => ({ default: () => null }))
vi.mock('../DefectTable', () => ({ default: () => null }))
vi.mock('../DefectFormDialog', () => ({ default: () => null }))
vi.mock('../DefectDetailSheet', () => ({
  default: ({ detail, open }: { detail: { title: string }; open: boolean }) => (
    open ? <div>深链缺陷：{detail.title}</div> : null
  ),
}))

afterEach(() => vi.clearAllMocks())

describe('DefectPage deep link', () => {
  it('loads the project-scoped defect and opens its detail sheet', async () => {
    apiMocks.fetchDefect.mockResolvedValue({ id: 7, title: '体育接口分诊缺陷' })

    render(
      <MemoryRouter initialEntries={['/defect/7']}>
        <Routes>
          <Route path="/defect/:id" element={<DefectPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => expect(apiMocks.fetchDefect).toHaveBeenCalledWith(7))
    expect(screen.getByText('深链缺陷：体育接口分诊缺陷')).not.toBeNull()
  })
})
