import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { VersionDiffResult } from '@/types'

const confirmVersionDiff = vi.fn()

vi.mock('@/api/releaseBundles', () => ({
  confirmVersionDiff: (...args: unknown[]) => confirmVersionDiff(...args),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const { default: DiffReviewPanel } = await import('./DiffReviewPanel')

const diffResult: VersionDiffResult = {
  new_modules: ['赛事回放'],
  modified_modules: [
    {
      module_name: '首页',
      parent_module_id: 12,
      change: 'modified',
      new_pages: ['赛事回放入口'],
      modified_pages: ['首页(PC端)'],
      deleted_pages: [],
      unchanged_pages: ['首页(Mobile)'],
    },
  ],
  deleted_modules: [],
  unchanged_modules: ['FAQ'],
  diff_confidence: 0.85,
  total_pages_diff: 2,
  warnings: [],
}

describe('DiffReviewPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    confirmVersionDiff.mockResolvedValue({
      created_modules: 4,
      module_ids: [1, 2, 3, 4],
      module_names: ['首页'],
    })
  })

  it('renders the backend diff contract and submits skipped module names', async () => {
    const onConfirm = vi.fn()
    render(
      <DiffReviewPanel
        bundleId={9}
        diffResult={diffResult}
        onConfirm={onConfirm}
      />,
    )

    expect(screen.getByText('赛事回放')).toBeTruthy()
    expect(screen.getByText('首页')).toBeTruthy()
    expect(screen.getByText(/置信度 85%/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /赛事回放/ }))
    fireEvent.click(screen.getByRole('button', { name: '跳过' }))
    fireEvent.click(screen.getByRole('button', { name: '确认全部' }))

    await waitFor(() => {
      expect(confirmVersionDiff).toHaveBeenCalledWith(9, {
        overrides: { skip_modules: ['赛事回放'] },
      })
    })
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('shows page-level changes for modified modules', () => {
    render(<DiffReviewPanel bundleId={9} diffResult={diffResult} />)
    fireEvent.click(screen.getByRole('button', { name: /首页/ }))

    expect(screen.getByText('赛事回放入口')).toBeTruthy()
    expect(screen.getByText('首页(PC端)')).toBeTruthy()
    expect(screen.getByText('首页(Mobile)')).toBeTruthy()
  })
})
