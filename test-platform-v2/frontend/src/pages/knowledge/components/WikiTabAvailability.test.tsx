import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  canManage: true,
  fetchWikiConfig: vi.fn(),
  fetchWikiRawSources: vi.fn(),
  fetchWikiPages: vi.fn(),
  fetchWikiSyncAvailability: vi.fn(),
  syncBundleToWiki: vi.fn(),
  toastSuccess: vi.fn(),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (state: { hasPerm: (permission: string) => boolean }) => unknown) =>
    selector({ hasPerm: (permission) => permission !== 'wiki:manage' || mocks.canManage }),
}))

vi.mock('@/api/wiki', () => ({
  fetchWikiConfig: (...args: unknown[]) => mocks.fetchWikiConfig(...args),
  fetchWikiRawSources: (...args: unknown[]) => mocks.fetchWikiRawSources(...args),
  fetchWikiPages: (...args: unknown[]) => mocks.fetchWikiPages(...args),
  fetchWikiSyncAvailability: (...args: unknown[]) => mocks.fetchWikiSyncAvailability(...args),
  syncBundleToWiki: (...args: unknown[]) => mocks.syncBundleToWiki(...args),
  fetchWikiPage: vi.fn(),
  fetchWikiPageLinks: vi.fn(),
  fetchWikiRawSource: vi.fn(),
  createWikiIngestJob: vi.fn(),
  approveWikiPage: vi.fn(),
  rejectWikiPage: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: { success: mocks.toastSuccess, error: vi.fn() },
}))

const { default: WikiTab } = await import('./WikiTab')

const available = {
  available: true,
  reason: '',
  release_bundle_id: 17,
  release_bundle_name: 'Batch 60 生产验收',
  release_bundle_status: 'active',
}

describe('WikiTab 同步前置条件', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.canManage = true
    mocks.fetchWikiConfig.mockResolvedValue({ wiki_enabled: true })
    mocks.fetchWikiRawSources.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
    mocks.fetchWikiPages.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 200 })
    mocks.fetchWikiSyncAvailability.mockResolvedValue(available)
    mocks.syncBundleToWiki.mockResolvedValue({
      release_bundle_id: 17,
      raw_sources_created: 2,
      raw_sources_updated: 0,
      raw_sources_skipped: 0,
      coverage: {},
      errors: [],
    })
  })

  it('无发布包时禁用同步并提供创建或选择发布包的入口', async () => {
    mocks.fetchWikiSyncAvailability.mockResolvedValue({
      available: false,
      reason: '当前项目暂无发布包，请先创建发布包并设为启用，或选择已有启用发布包。',
      release_bundle_id: null,
      release_bundle_name: '',
      release_bundle_status: '',
    })

    render(<WikiTab />)

    const button = await screen.findByRole('button', { name: '同步发布包到 Wiki' })
    expect(button.getAttribute('disabled')).not.toBeNull()
    expect(screen.getByText(/当前项目暂无发布包/)).toBeTruthy()
    expect(screen.getByRole('link', { name: '前往发布包管理' }).getAttribute('href'))
      .toBe('/release-bundles')
    fireEvent.click(button)
    expect(mocks.syncBundleToWiki).not.toHaveBeenCalled()
  })

  it('有效发布包允许真实同步并报告写入计数', async () => {
    render(<WikiTab />)

    const button = await screen.findByRole('button', { name: '同步发布包到 Wiki' })
    expect(button.getAttribute('disabled')).toBeNull()
    fireEvent.click(button)

    await waitFor(() => expect(mocks.syncBundleToWiki).toHaveBeenCalledWith(17))
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Wiki 同步完成：新增 2，更新 0，跳过 0')
  })

  it('缺少管理权限时保持同步禁用且不触发请求', async () => {
    mocks.canManage = false

    render(<WikiTab />)

    const button = await screen.findByRole('button', { name: '同步发布包到 Wiki' })
    expect(button.getAttribute('disabled')).not.toBeNull()
    expect(screen.getByText('当前账号缺少 Wiki 管理权限，无法同步发布包。')).toBeTruthy()
    fireEvent.click(button)
    expect(mocks.syncBundleToWiki).not.toHaveBeenCalled()
  })
})
