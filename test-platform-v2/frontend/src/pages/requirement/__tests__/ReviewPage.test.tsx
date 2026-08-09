import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mockFetchReviewState = vi.fn()
const mockReviewCase = vi.fn()
const mockReviewImportCases = vi.fn()

vi.mock('@/api/requirement', () => ({
  fetchReviewState: (...args: unknown[]) => mockFetchReviewState(...args),
  reviewCase: (...args: unknown[]) => mockReviewCase(...args),
  reviewImportCases: (...args: unknown[]) => mockReviewImportCases(...args),
  generateTestCasesAsync: vi.fn(),
  runAsyncAiTask: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}))

const { default: ReviewPage } = await import('../ReviewPage')

function reviewState() {
  return {
    document_title: 'Batch 48 审查文档',
    functional_cases: [{
      index: 4,
      title: '原始标题',
      priority: 'P0',
      module: '审查',
      domain: '需求',
      preconditions: '',
      steps: '[]',
      expected_result: '原始预期',
      case_type: 'manual',
      review_status: 'edited',
      edited_data: {
        title: '已持久化编辑标题',
        expected_result: '已持久化编辑预期',
      },
      imported: false,
    }],
    api_cases: [],
    summary: {
      total: 1,
      approved: 0,
      rejected: 0,
      pending: 1,
    },
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/requirement/42/review']}>
      <Routes>
        <Route path="/requirement/:id/review" element={<ReviewPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ReviewPage durable review flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchReviewState.mockResolvedValue(reviewState())
    mockReviewCase.mockResolvedValue({ review_status: 'edited' })
    mockReviewImportCases.mockResolvedValue({ imported: 1, skipped: 0, total: 1 })
  })

  afterEach(() => cleanup())

  it('restores persisted edits and imports the selected canonical index', async () => {
    renderPage()

    const openCase = await screen.findByRole('button', {
      name: '查看用例：已持久化编辑标题',
    })
    expect(screen.getByText('已持久化编辑标题')).toBeTruthy()

    fireEvent.click(screen.getByRole('checkbox', {
      name: '选择用例：已持久化编辑标题',
    }))
    fireEvent.click(screen.getByRole('button', { name: '导入选中用例 (1)' }))

    await waitFor(() => expect(mockReviewImportCases).toHaveBeenCalledWith(42, [4]))
    expect(openCase).toBeTruthy()
  })

  it('saves edited values through the persistent review endpoint', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', {
      name: '查看用例：已持久化编辑标题',
    }))
    fireEvent.click(screen.getByRole('button', { name: '编辑' }))
    fireEvent.change(screen.getByLabelText('用例标题'), {
      target: { value: 'Batch 48 最终标题' },
    })
    fireEvent.click(screen.getByRole('button', { name: '保存编辑' }))

    await waitFor(() => expect(mockReviewCase).toHaveBeenCalledWith(
      42,
      4,
      'edit',
      expect.objectContaining({
        title: 'Batch 48 最终标题',
        expected_result: '已持久化编辑预期',
      }),
    ))
  })

  it('paginates large review queues instead of mounting every case at once', async () => {
    mockFetchReviewState.mockResolvedValue({
      ...reviewState(),
      functional_cases: Array.from({ length: 120 }, (_, index) => ({
        ...reviewState().functional_cases[0],
        index,
        title: `批量用例 ${index + 1}`,
        edited_data: null,
        review_status: 'pending',
      })),
      summary: { total: 120, approved: 0, rejected: 0, pending: 120 },
    })

    renderPage()

    expect(await screen.findByRole('button', { name: '查看用例：批量用例 1' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: '查看用例：批量用例 51' })).toBeNull()
    expect(screen.getByText('第 1 / 3 页')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '下一页' }))

    expect(await screen.findByRole('button', { name: '查看用例：批量用例 51' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: '查看用例：批量用例 1' })).toBeNull()
  })
})
