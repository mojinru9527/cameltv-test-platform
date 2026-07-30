import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const useApiMock = vi.hoisted(() => vi.fn())
const fetchRegressionScope = vi.hoisted(() => vi.fn())

vi.mock('@/hooks/useApi', () => ({
  useApi: (...args: unknown[]) => useApiMock(...args),
}))
vi.mock('@/hooks/useDocumentTitle', () => ({
  useDocumentTitle: vi.fn(),
}))
vi.mock('@/api/releaseBundles', () => ({
  fetchReleaseBundle: vi.fn(),
  updateReleaseBundle: vi.fn(),
  fetchVersionChain: vi.fn(),
  triggerVersionDiff: vi.fn(),
  fetchRegressionScope: (...args: unknown[]) => fetchRegressionScope(...args),
  triggerRegression: vi.fn(),
}))
vi.mock('@/api/requirementModules', () => ({
  fetchModuleTree: vi.fn(),
}))
vi.mock('@/pages/release-bundles/components/ModuleTreeView', () => ({
  default: () => <div>module tree</div>,
}))
vi.mock('@/pages/release-bundles/components/VersionChainTimeline', () => ({
  default: () => <div>version chain</div>,
}))
vi.mock('@/pages/release-bundles/components/DiffReviewPanel', () => ({
  default: () => <div>diff review</div>,
}))

import BundleDetailPage from '../BundleDetail'

const bundle = {
  id: 52,
  name: 'Batch 52',
  description: '',
  client_version: '',
  admin_version: '',
  status: 'draft',
  parent_bundle_id: null,
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/release-bundles/52']}>
      <Routes>
        <Route path="/release-bundles/:id" element={<BundleDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('release bundle icon actions', () => {
  beforeEach(() => {
    let callIndex = 0
    const states = [
      { data: bundle, isLoading: false, isError: false, refetch: vi.fn(), setData: vi.fn() },
      { data: [], isLoading: false, isError: false, refetch: vi.fn(), setData: vi.fn() },
      {
        data: { total_modules: 0, total_pages: 0, total_attachments: 0 },
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
        setData: vi.fn(),
      },
    ]
    useApiMock.mockReset().mockImplementation(() => states[callIndex++ % states.length])
    fetchRegressionScope.mockReset().mockResolvedValue({
      changed_modules: [],
      total_regression_cases: 0,
      selected_cases: [],
    })
  })

  it('names the back navigation action', () => {
    renderPage()
    expect(screen.getByRole('button', { name: '返回发布包列表' })).toBeTruthy()
  })

  it('names the regression-scope close action', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: '回归范围' }))

    expect(await screen.findByRole('button', { name: '关闭回归范围' })).toBeTruthy()
  })
})
