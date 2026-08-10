import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockFetchGraphView = vi.fn()
const mockTriggerEntityExtract = vi.fn()
const mockFetchEntityStats = vi.fn()

vi.mock('@/api/knowledge', () => ({
  fetchEntityStats: (...args: unknown[]) => mockFetchEntityStats(...args),
  fetchGraphView: (...args: unknown[]) => mockFetchGraphView(...args),
  triggerEntityExtract: (...args: unknown[]) => mockTriggerEntityExtract(...args),
  evolveGraph: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('vis-network', () => ({
  Network: class {
    on = vi.fn()
    destroy = vi.fn()
    moveTo = vi.fn()
    getScale = vi.fn(() => 1)
    fit = vi.fn()
    body = { data: { nodes: { forEach: vi.fn(), update: vi.fn() } } }
  },
}))
vi.mock('vis-data', () => ({
  DataSet: class {
    get = vi.fn()
    update = vi.fn()
    forEach = vi.fn()
  },
}))

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

describe('GraphTab case-count legend', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchGraphView.mockResolvedValue({
      nodes: [
        { id: 'test_case:tc1', entity_type: 'test_case', name: '用例A', group: 'test_case', description: '', confidence: 1, entity_id: 1 },
        { id: 'module:m1', entity_type: 'module', name: '模块A', group: 'module', description: '', confidence: 1, entity_id: 2 },
      ],
      edges: [],
      extract_available: true,
      unavailable_reason: '',
    })
    mockFetchEntityStats.mockResolvedValue({
      total: 527,
      by_type: { test_case: 526, module: 1 },
      missing_source: 0,
      test_case_total: 7559,
    })
  })

  it('shows authoritative ingested/total count for test cases in the legend', async () => {
    const { default: GraphTab } = await import('./GraphTab')
    render(<GraphTab />)

    expect(await screen.findByText('526/7559 已入库')).toBeTruthy()
  })
})