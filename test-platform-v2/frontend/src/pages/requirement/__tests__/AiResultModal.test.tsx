import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AIGenerateResult } from '@/types'

const mockReviewCase = vi.fn()
const mockImportCases = vi.fn()
const mockToastWarning = vi.fn()

vi.mock('@/api/requirement', () => ({
  reviewCase: (...args: unknown[]) => mockReviewCase(...args),
  importCases: (...args: unknown[]) => mockImportCases(...args),
  confirmExtraction: vi.fn(),
  generateTestCases: vi.fn(),
  matchApiEndpoints: vi.fn(),
  fetchApiMatchSelection: vi.fn(),
  confirmApiMatches: vi.fn(),
}))

vi.mock('@/api/apitest', () => ({
  fetchApiServices: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: (...args: unknown[]) => mockToastWarning(...args),
  },
}))

const { default: AiResultModal } = await import('../AiResultModal')

const result: AIGenerateResult = {
  document_id: 5,
  functional_cases: [{
    index: 0,
    title: 'original title',
    case_type: 'manual',
    priority: 'P1',
    domain: '需求',
    module: '编辑导入',
    preconditions: '',
    steps: '[]',
    expected_result: 'original result',
    api_method: '',
    api_endpoint: '',
    remark: '',
    imported: false,
  }],
  api_cases: [],
  raw_response: '{}',
}

function renderModal() {
  return render(
    <AiResultModal
      open
      result={result}
      extractionResult={null}
      documentId={5}
      mode="generate"
      onClose={vi.fn()}
      onImportSuccess={vi.fn()}
      onExtractionConfirmAndGenerate={vi.fn()}
      onExtractionReject={vi.fn()}
    />,
  )
}

describe('AiResultModal edited import flow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockReviewCase.mockResolvedValue({ review_status: 'edited' })
    mockImportCases.mockResolvedValue({ imported: 1, skipped: 0, total: 1 })
  })

  afterEach(() => cleanup())

  it('persists an edit and imports the final edited value', async () => {
    renderModal()
    fireEvent.click(screen.getByRole('button', { name: '编辑用例' }))
    fireEvent.change(screen.getByPlaceholderText('用例标题'), {
      target: { value: 'edited title' },
    })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => expect(mockReviewCase).toHaveBeenCalledWith(
      5,
      0,
      'edit',
      expect.objectContaining({ title: 'edited title' }),
    ))

    const rowCheckbox = screen.getAllByRole('checkbox')[1]
    fireEvent.click(rowCheckbox)
    fireEvent.click(screen.getByRole('button', { name: '导入功能用例 (1)' }))

    await waitFor(() => expect(mockImportCases).toHaveBeenCalledWith(
      5,
      [0],
      [expect.objectContaining({ index: 0, title: 'edited title' })],
    ))
  })

  it('keeps failed edits open and blocks importing stale original data', async () => {
    mockReviewCase.mockRejectedValue(new Error('save failed'))
    renderModal()

    fireEvent.click(screen.getByRole('button', { name: '编辑用例' }))
    fireEvent.change(screen.getByPlaceholderText('用例标题'), {
      target: { value: 'unsaved title' },
    })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))
    await waitFor(() => expect(mockReviewCase).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: '导入功能用例 (1)' }))

    expect(mockImportCases).not.toHaveBeenCalled()
    expect(mockToastWarning).toHaveBeenCalledWith('请先保存或取消正在编辑的用例')
    expect(screen.getByDisplayValue('unsaved title')).toBeTruthy()
  })
})
