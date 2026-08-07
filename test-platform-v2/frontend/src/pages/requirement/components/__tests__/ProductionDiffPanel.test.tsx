import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const mockListBundles = vi.fn()
const mockProductionDiff = vi.fn()
const mockGetCaptureTask = vi.fn()

vi.mock('@/api/requirement', () => ({
  listReleaseBundles: (...a: unknown[]) => mockListBundles(...a),
  productionDiff: (...a: unknown[]) => mockProductionDiff(...a),
  getCaptureTask: (...a: unknown[]) => mockGetCaptureTask(...a),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

const { default: ProductionDiffPanel } = await import('../ProductionDiffPanel')

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ProductionDiffPanel (C102-4)', () => {
  it('loads bundles and renders empty state', async () => {
    mockListBundles.mockResolvedValue({ items: [], total: 0 })
    render(<ProductionDiffPanel />)
    await waitFor(() => expect(screen.getByText('生产差异标注（C102-4）')).toBeTruthy())
    expect(screen.getByPlaceholderText(/match-replay/)).toBeTruthy()
  })

  it('generates diff and renders summary + items', async () => {
    mockListBundles.mockResolvedValue({
      items: [{ id: 1, name: '体育平台-生产', client_version: '14.2.0', status: 'active' }],
      total: 1,
    })
    mockProductionDiff.mockResolvedValue({
      summary: { production_total: 2, requirement_total: 2, new_count: 1, matched_count: 1, missing_count: 1 },
      items: [
        { name: 'match-replay', change_type: 'new' },
        { name: '首页', change_type: 'matched', matched_with: '首页' },
        { name: '个人中心', change_type: 'missing' },
      ],
      warnings: [],
    })
    render(<ProductionDiffPanel />)
    await waitFor(() => expect(mockListBundles).toHaveBeenCalled())
    fireEvent.change(screen.getByLabelText('生产页面清单（每行一个）'), {
      target: { value: 'match-replay\n首页' },
    })
    fireEvent.click(screen.getByRole('button', { name: '生成差异' }))
    await waitFor(() => expect(mockProductionDiff).toHaveBeenCalledWith(1, [{ label: 'match-replay' }, { label: '首页' }]))
    await waitFor(() => expect(screen.getByText('新增 1')).toBeTruthy())
    expect(screen.getByText('一致 1')).toBeTruthy()
    expect(screen.getByText('缺失 1')).toBeTruthy()
    expect(screen.getByText('match-replay')).toBeTruthy()
    expect(screen.getByText('个人中心')).toBeTruthy()
  })

  it('shows error message when generation fails', async () => {
    mockListBundles.mockResolvedValue({ items: [{ id: 1, name: 'b', client_version: '1', status: 'active' }], total: 1 })
    mockProductionDiff.mockRejectedValue(new Error('接口失败'))
    render(<ProductionDiffPanel />)
    await waitFor(() => expect(mockListBundles).toHaveBeenCalled())
    fireEvent.change(screen.getByLabelText('生产页面清单（每行一个）'), { target: { value: '首页' } })
    fireEvent.click(screen.getByRole('button', { name: '生成差异' }))
    await waitFor(() => expect(screen.getByText('接口失败')).toBeTruthy())
  })
})


describe('ProductionDiffPanel capture loading (C119-1)', () => {
  it('loads capture task pages into the textarea', async () => {
    mockListBundles.mockResolvedValue({ items: [{ id: 1, name: 'b', client_version: '1', status: 'active' }], total: 1 })
    mockGetCaptureTask.mockResolvedValue({
      task_id: 'cap-1',
      status: 'done',
      pages: ['https://www.camel1.tv/match-replay', '/worldcup-2026'],
      samples: [],
    })
    mockProductionDiff.mockResolvedValue({
      summary: { production_total: 2, requirement_total: 1, new_count: 1, matched_count: 1, missing_count: 1 },
      items: [{ name: 'match-replay', change_type: 'new' }, { name: '首页', change_type: 'matched', matched_with: '首页' }],
      warnings: [],
    })
    render(<ProductionDiffPanel />)
    await waitFor(() => expect(mockListBundles).toHaveBeenCalled())
    fireEvent.change(screen.getByLabelText('采集任务 ID'), { target: { value: 'cap-1' } })
    fireEvent.click(screen.getByRole('button', { name: '加载采集' }))
    await waitFor(() => expect(mockGetCaptureTask).toHaveBeenCalledWith('cap-1'))
    const textarea = screen.getByLabelText('生产页面清单（每行一个）') as HTMLTextAreaElement
    expect(textarea.value).toContain('match-replay')
    expect(textarea.value).toContain('worldcup-2026')
    fireEvent.click(screen.getByRole('button', { name: '生成差异' }))
    await waitFor(() => expect(mockProductionDiff).toHaveBeenCalled())
  })

  it('warns when capture task is not done', async () => {
    mockListBundles.mockResolvedValue({ items: [], total: 0 })
    mockGetCaptureTask.mockResolvedValue({ task_id: 'cap-2', status: 'running', pages: [], samples: [] })
    render(<ProductionDiffPanel />)
    await waitFor(() => expect(mockListBundles).toHaveBeenCalled())
    fireEvent.change(screen.getByLabelText('采集任务 ID'), { target: { value: 'cap-2' } })
    fireEvent.click(screen.getByRole('button', { name: '加载采集' }))
    await waitFor(() => expect(mockGetCaptureTask).toHaveBeenCalledWith('cap-2'))
  })
})
