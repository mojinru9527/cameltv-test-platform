import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockFetchGraphView = vi.fn()
const mockTriggerEntityExtract = vi.fn()

vi.mock('@/api/knowledge', () => ({
  fetchGraphView: (...args: unknown[]) => mockFetchGraphView(...args),
  triggerEntityExtract: (...args: unknown[]) => mockTriggerEntityExtract(...args),
  evolveGraph: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('vis-network', () => ({ Network: vi.fn() }))
vi.mock('vis-data', () => ({ DataSet: vi.fn() }))

describe('GraphTab extraction availability', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('disables extraction and explains the empty knowledge prerequisite', async () => {
    mockFetchGraphView.mockResolvedValue({
      nodes: [],
      edges: [],
      extract_available: false,
      unavailable_reason: '当前项目没有可提取的有效知识片段，请先导入并解析知识源',
    })

    const { default: GraphTab } = await import('./GraphTab')
    render(<GraphTab />)

    expect(await screen.findByText('当前项目没有可提取的有效知识片段，请先导入并解析知识源')).toBeTruthy()
    const extractButton = screen.getByRole('button', { name: '触发实体提取' })
    expect((extractButton as HTMLButtonElement).disabled).toBe(true)

    fireEvent.click(extractButton)
    expect(mockTriggerEntityExtract).not.toHaveBeenCalled()
  })
})
