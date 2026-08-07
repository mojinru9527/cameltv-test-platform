import { StrictMode } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'

const mockFetchDomains = vi.fn()
const mockFetchRequirements = vi.fn()
const mockFetchRequirement = vi.fn()
const mockFetchRequirementCoverage = vi.fn()
const mockConfirmExtraction = vi.fn()
const mockExtractFeatures = vi.fn()
const mockGenerateTestCases = vi.fn()
const mockExtractFeaturesAsync = vi.fn()
const mockGenerateTestCasesAsync = vi.fn()
const mockRunAsyncAiTask = vi.fn()

vi.mock('@/api/testcase', () => ({
  fetchDomains: (...args: unknown[]) => mockFetchDomains(...args),
}))

vi.mock('@/api/requirement', () => ({
  fetchRequirements: (...args: unknown[]) => mockFetchRequirements(...args),
  fetchRequirement: (...args: unknown[]) => mockFetchRequirement(...args),
  fetchRequirementCoverage: (...args: unknown[]) => mockFetchRequirementCoverage(...args),
  confirmExtraction: (...args: unknown[]) => mockConfirmExtraction(...args),
  deleteRequirement: vi.fn(),
  extractFeatures: (...args: unknown[]) => mockExtractFeatures(...args),
  extractFeaturesAsync: (...args: unknown[]) => mockExtractFeaturesAsync(...args),
  generateTestCasesAsync: (...args: unknown[]) => mockGenerateTestCasesAsync(...args),
  runAsyncAiTask: (...args: unknown[]) => mockRunAsyncAiTask(...args),
  fetchGeneratedCases: vi.fn(),
  generateTestCases: (...args: unknown[]) => mockGenerateTestCases(...args),
  getOrCreateExtraction: vi.fn(),
  uploadRequirement: vi.fn(),
}))

vi.mock('react-dropzone', () => ({
  useDropzone: () => ({
    getRootProps: () => ({}),
    getInputProps: () => ({}),
    isDragActive: false,
  }),
}))

vi.mock('@/pages/requirement/AiResultModal', () => ({ default: () => null }))
vi.mock('@/pages/requirement/components/EvidenceTaskPanel', () => ({ default: () => null }))
vi.mock('@/pages/requirement/components/VersionCompare', () => ({ default: () => null }))
vi.mock('@/pages/requirement/components/PrototypePreview', () => ({ default: () => null }))
vi.mock('@/pages/knowledge/components/LanhuEvidenceDialog', () => ({ default: () => null }))
vi.mock('@/pages/knowledge/components/LanhuEvidenceJobDrawer', () => ({ default: () => null }))
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}))

const { default: RequirementPage } = await import('../index')

function brief(id: number, title: string) {
  return {
    id,
    title,
    source_ref: `${title}.md`,
    file_type: 'md',
    status: 'uploaded',
    extraction_status: 'none',
    imported_func_count: 0,
    imported_api_count: 0,
    creator_name: 'Batch 48 QA',
    created_at: '2026-07-27T08:00:00Z',
  }
}

function renderPage() {
  return render(
    <StrictMode>
      <MemoryRouter initialEntries={['/requirement']}>
        <RequirementPage />
      </MemoryRouter>
    </StrictMode>,
  )
}

describe('RequirementPage acceptance behavior', () => {
  beforeEach(() => {
    useAuthStore.setState({ permissions: ['*'], currentProjectId: 1 })
    vi.clearAllMocks()
    mockFetchDomains.mockResolvedValue([])
    mockFetchRequirements.mockResolvedValue({
      total: 101,
      page: 1,
      page_size: 10,
      items: [brief(1, '第一页需求')],
    })
    mockFetchRequirement.mockResolvedValue({
      ...brief(1, '第一页需求'),
      content: '这是按需加载的完整正文',
    })
    mockFetchRequirementCoverage.mockResolvedValue({
      document_id: 1,
      total_requirements: 4,
      covered_requirements: 3,
      coverage_rate: 75,
    })
    mockConfirmExtraction.mockResolvedValue({ extraction_status: 'rejected' })
    mockExtractFeatures.mockResolvedValue({
      document_id: 1,
      modules: [],
      overall_assessment: '重新拆分完成',
      raw_response: '{}',
      extraction_status: 'pending_review',
    })
    mockGenerateTestCases.mockResolvedValue({
      document_id: 1,
      functional_cases: [],
      api_cases: [],
      raw_response: '{}',
    })
  })

  afterEach(() => cleanup())

  it('issues one initial list request, shows creator and loads full detail on demand', async () => {
    renderPage()

    expect(await screen.findByText('第一页需求')).toBeTruthy()
    expect(screen.getByText('Batch 48 QA')).toBeTruthy()
    expect(mockFetchRequirements).toHaveBeenCalledTimes(1)
    expect(mockFetchRequirement).not.toHaveBeenCalled()

    mockGenerateTestCasesAsync.mockResolvedValue({ id: 'ai-g1', status: 'running' })
    mockRunAsyncAiTask.mockResolvedValue({ functional_cases: [] })
    fireEvent.click(screen.getByRole('button', { name: '预览需求文档：第一页需求' }))

    expect(await screen.findByText('这是按需加载的完整正文')).toBeTruthy()
    expect(await screen.findByText('75%')).toBeTruthy()
    expect(mockFetchRequirement).toHaveBeenCalledTimes(1)
    expect(mockFetchRequirementCoverage).toHaveBeenCalledTimes(1)
  })

  it('sends pagination and debounced search to the server instead of filtering one page locally', async () => {
    renderPage()
    await screen.findByText('第一页需求')

    const next = screen
      .getAllByRole('button', { name: '下一页' })
      .find((button) => !(button as HTMLButtonElement).disabled)
    expect(next).toBeTruthy()
    fireEvent.click(next!)

    await waitFor(() => expect(mockFetchRequirements).toHaveBeenCalledWith(
      { page: 2, page_size: 10 },
      expect.any(AbortSignal),
    ))

    fireEvent.change(screen.getByPlaceholderText('搜索文档'), {
      target: { value: '跨页命中' },
    })

    await waitFor(() => expect(mockFetchRequirements).toHaveBeenCalledWith(
      { page: 1, page_size: 10, keyword: '跨页命中' },
      expect.any(AbortSignal),
    ))
  })

  it('keeps confirmed generation and re-extraction as two distinct actions', async () => {
    mockFetchRequirements.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 10,
      items: [{ ...brief(1, '已确认拆分'), extraction_status: 'confirmed' }],
    })

    renderPage()
    await screen.findByText('已确认拆分')

    fireEvent.click(screen.getByRole('button', { name: '生成用例(基于拆分)' }))
    await waitFor(() => expect(mockGenerateTestCasesAsync).toHaveBeenCalledWith(
      1,
      { use_extraction: true },
    ))
    expect(mockRunAsyncAiTask).toHaveBeenCalledWith('ai-g1')

    fireEvent.click(screen.getByRole('button', { name: '重新拆分' }))
    await waitFor(() => {
      expect(mockConfirmExtraction).toHaveBeenCalledWith(1, {
        action: 'reject',
        rejected_notes: '用户主动重新拆分',
      })
      expect(mockExtractFeaturesAsync).toHaveBeenCalledWith(1)
    })
    expect(mockGenerateTestCasesAsync).toHaveBeenCalledTimes(1)
  })
})
