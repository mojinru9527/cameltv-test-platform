import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const fetchKnowledgeSources = vi.fn()
const fetchSourceChunks = vi.fn()
const verifyKnowledgeSource = vi.fn()
const fetchReleaseBundles = vi.fn()
const fetchSyncCoverage = vi.fn()

vi.mock('@/api/knowledge', () => ({
  fetchKnowledgeSources: (...args: unknown[]) => fetchKnowledgeSources(...args),
  fetchSourceChunks: (...args: unknown[]) => fetchSourceChunks(...args),
  verifyKnowledgeSource: (...args: unknown[]) => verifyKnowledgeSource(...args),
}))

vi.mock('@/api/releaseBundles', () => ({
  fetchReleaseBundles: (...args: unknown[]) => fetchReleaseBundles(...args),
}))

vi.mock('@/api/wiki', () => ({
  fetchSyncCoverage: (...args: unknown[]) => fetchSyncCoverage(...args),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const { default: SourceListTab } = await import('../SourceListTab')

const sources = [
  {
    id: 1,
    project_id: 1,
    source_type: 'requirement',
    source_id: 11,
    title: '用户端需求',
    source_ref: 'USER-REQ',
    version: '1',
    status: 'active',
    created_at: '2026-07-29T00:00:00Z',
  },
  {
    id: 2,
    project_id: 1,
    source_type: 'requirement',
    source_id: 12,
    title: '运营后台需求',
    source_ref: 'ADMIN-REQ',
    version: '1',
    status: 'active',
    created_at: '2026-07-29T00:00:00Z',
  },
]

function coverage(overrides: Record<string, number> = {}) {
  return {
    total_pages: 4,
    synced_pages: 4,
    stale_pages: 0,
    missing_pages: 0,
    coverage_rate: 1,
    ...overrides,
  }
}

describe('SourceListTab Wiki sync badge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchKnowledgeSources.mockResolvedValue({
      items: sources,
      total: sources.length,
      page: 1,
      page_size: 20,
    })
    fetchReleaseBundles.mockResolvedValue({
      items: [{ id: 17, name: 'v57', status: 'active' }],
      total: 1,
      page: 1,
      page_size: 1,
    })
  })

  it('shows loading while the latest bundle coverage is pending', async () => {
    fetchSyncCoverage.mockReturnValue(new Promise(() => {}))

    render(<SourceListTab />)

    await waitFor(() => expect(fetchSyncCoverage).toHaveBeenCalledTimes(1))
    expect(screen.getByLabelText('Wiki 同步状态加载中')).toBeTruthy()
  })

  it('shows synced and requests coverage once for multiple source rows', async () => {
    fetchSyncCoverage.mockResolvedValue(coverage())

    render(<SourceListTab />)

    expect(await screen.findByText('已同步')).toBeTruthy()
    expect(await screen.findByText('用户端需求')).toBeTruthy()
    expect(await screen.findByText('运营后台需求')).toBeTruthy()
    expect(fetchReleaseBundles).toHaveBeenCalledTimes(1)
    expect(fetchSyncCoverage).toHaveBeenCalledTimes(1)
  })

  it('shows partial when only part of the bundle is current', async () => {
    fetchSyncCoverage.mockResolvedValue(coverage({
      synced_pages: 2,
      stale_pages: 1,
      missing_pages: 1,
      coverage_rate: 0.5,
    }))

    render(<SourceListTab />)

    expect(await screen.findByText('部分同步')).toBeTruthy()
  })

  it('shows failed when the active bundle has no synced pages', async () => {
    fetchSyncCoverage.mockResolvedValue(coverage({
      synced_pages: 0,
      missing_pages: 4,
      coverage_rate: 0,
    }))

    render(<SourceListTab />)

    expect(await screen.findByText('同步失败')).toBeTruthy()
  })

  it('shows an error state when coverage cannot be loaded', async () => {
    fetchSyncCoverage.mockRejectedValue(new Error('network unavailable'))

    render(<SourceListTab />)

    expect(await screen.findByText('状态异常')).toBeTruthy()
  })
})
