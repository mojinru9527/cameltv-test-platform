import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mockDownloadAsset = vi.fn()

vi.mock('@/api/lanhuEvidence', () => ({
  downloadLanhuEvidenceAsset: (...args: unknown[]) => mockDownloadAsset(...args),
}))

const { default: PrototypePreview } = await import('../PrototypePreview')

describe('PrototypePreview', () => {
  const createObjectURL = vi.fn(() => 'blob:asset-17')
  const revokeObjectURL = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL,
      revokeObjectURL,
    })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('loads an authenticated asset Blob and revokes its object URL on cleanup', async () => {
    mockDownloadAsset.mockResolvedValue(new Blob(['png'], { type: 'image/png' }))

    const view = render(
      <PrototypePreview
        open
        onClose={vi.fn()}
        pages={[{
          page_name: '登录页',
          page_index: 0,
          asset_id: 17,
          ocr_text: '手机号登录',
        }]}
      />,
    )

    const image = await screen.findByAltText('登录页')
    expect(image.getAttribute('src')).toBe('blob:asset-17')
    expect(mockDownloadAsset).toHaveBeenCalledWith(17, expect.any(AbortSignal))
    expect(screen.getByText('手机号登录')).toBeTruthy()
    expect(screen.getByRole('button', { name: '放大截图' })).toBeTruthy()

    view.unmount()
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith('blob:asset-17'))
  })

  it('shows a readable fallback when a page has no screenshot asset', () => {
    render(
      <PrototypePreview
        open
        onClose={vi.fn()}
        pages={[{ page_name: '空页面', page_index: 0 }]}
      />,
    )

    expect(screen.getByText('该页面没有截图资产')).toBeTruthy()
    expect(mockDownloadAsset).not.toHaveBeenCalled()
  })
})
