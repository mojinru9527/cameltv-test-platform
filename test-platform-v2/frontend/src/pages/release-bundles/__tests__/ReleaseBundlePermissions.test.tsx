import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/stores/auth'

const useApiMock = vi.hoisted(() => vi.fn())

vi.mock('@/hooks/useApi', () => ({
  useApi: (...args: unknown[]) => useApiMock(...args),
}))
vi.mock('@/hooks/useDocumentTitle', () => ({
  useDocumentTitle: vi.fn(),
}))
vi.mock('@/api/releaseBundles', () => ({
  createReleaseBundle: vi.fn(),
  deleteReleaseBundle: vi.fn(),
  fetchReleaseBundles: vi.fn(),
  fetchReleaseBundle: vi.fn(),
  updateReleaseBundle: vi.fn(),
  fetchVersionChain: vi.fn(),
  triggerVersionDiff: vi.fn(),
  fetchRegressionScope: vi.fn(),
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
import ReleaseBundlesPage from '../index'

const bundle = {
  id: 60,
  name: 'Batch 60 sports release',
  description: '',
  client_version: '60.0.0',
  admin_version: '60.0.0',
  status: 'draft',
  parent_bundle_id: 59,
  module_count: 1,
  page_count: 1,
  created_at: '2026-08-01T00:00:00Z',
}

describe('release bundle management permissions', () => {
  beforeEach(() => {
    useAuthStore.setState({ permissions: ['knowledge:view'] })
  })

  it('hides create and delete controls from read-only users on the list', () => {
    useApiMock.mockReset().mockReturnValue({
      data: { items: [bundle], total: 1, page: 1, page_size: 20 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    })

    render(
      <MemoryRouter initialEntries={['/release-bundles']}>
        <Routes>
          <Route path="/release-bundles" element={<ReleaseBundlesPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByRole('button', { name: '新建发布包' })).toBeNull()
    expect(screen.queryByRole('button', { name: `删除发布包 ${bundle.name}` })).toBeNull()
  })

  it('hides management actions from read-only users on the detail page', () => {
    let callIndex = 0
    const states = [
      { data: bundle, isLoading: false, isError: false, refetch: vi.fn(), setData: vi.fn() },
      { data: [], isLoading: false, isError: false, refetch: vi.fn(), setData: vi.fn() },
      {
        data: { total_modules: 0, total_pages: 0, total_attachments: 0, roots: [] },
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
        setData: vi.fn(),
      },
    ]
    useApiMock.mockReset().mockImplementation(() => states[callIndex++ % states.length])

    render(
      <MemoryRouter initialEntries={['/release-bundles/60']}>
        <Routes>
          <Route path="/release-bundles/:id" element={<BundleDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByRole('button', { name: '编辑' })).toBeNull()
    expect(screen.queryByRole('button', { name: '触发UI回归' })).toBeNull()
    expect(screen.queryByRole('button', { name: '触发对比' })).toBeNull()
  })
})
