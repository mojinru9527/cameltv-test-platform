import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AIGenerateResult, CoverageReport } from '@/types'

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
      false,
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

    // When the row is still in edit mode (save failed), the row checkbox is absent;
    // use the select-all checkbox [0] instead — it selects all indices regardless.
    const selectAll = screen.getAllByRole('checkbox')[0]
    fireEvent.click(selectAll)
    fireEvent.click(screen.getByRole('button', { name: '导入功能用例 (1)' }))

    expect(mockImportCases).not.toHaveBeenCalled()
    expect(mockToastWarning).toHaveBeenCalledWith('请先保存或取消正在编辑的用例')
    expect(screen.getByDisplayValue('unsaved title')).toBeTruthy()
  })
})


describe('AiResultModal coverage report tab (C117-1)', () => {
  const coverage: CoverageReport = {
    matrix: [
      { module: '首页', function_point: '热门比赛', covered: true, case_count: 2 },
      { module: '首页', function_point: '赛程表', covered: false, case_count: 0 },
    ],
    gaps: [{ module: '首页', function_point: '赛程表' }],
    gap_count: 1,
    total_fp: 2,
    covered_fp: 1,
    coverage_rate: 0.5,
  }

  it('renders coverage tab with matrix and gaps', async () => {
    const withCoverage: AIGenerateResult = {
      ...result,
      coverage_report: coverage,
    }
    render(
      <AiResultModal
        open
        result={withCoverage}
        extractionResult={null}
        documentId={5}
        mode="generate"
        onClose={vi.fn()}
        onImportSuccess={vi.fn()}
        onExtractionConfirmAndGenerate={vi.fn()}
        onExtractionReject={vi.fn()}
      />,
    )
    const covTab = screen.getByRole('tab', { name: /覆盖矩阵/ })
    fireEvent.mouseDown(covTab, { button: 0 })
    fireEvent.click(covTab)
    await waitFor(() => expect(screen.getByText(/50\.0%/)).toBeTruthy())
    expect(screen.getAllByText(/赛程表/).length).toBeGreaterThan(0)
    expect(screen.getByText(/未覆盖/)).toBeTruthy()
    expect(screen.getByText(/覆盖缺口/)).toBeTruthy()
  })

  it('hides coverage tab when report is absent', () => {
    renderModal()
    expect(screen.queryByRole('tab', { name: /覆盖矩阵/ })).toBeNull()
  })
})
