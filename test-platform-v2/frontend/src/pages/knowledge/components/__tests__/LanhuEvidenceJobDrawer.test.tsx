import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const { default: LanhuEvidenceJobDrawer } = await import('../LanhuEvidenceJobDrawer')
const { useAuthStore } = await import('@/stores/auth')

const job = {
  id: 17,
  project_id: 1,
  source_url: 'https://lanhuapp.com/x?docId=d',
  doc_id: 'd',
  version_id: '',
  root_page_id: 'root',
  document_name: 'Release evidence',
  status: 'success_with_warnings',
  stage: 'done',
  total_pages: 3,
  captured_pages: 2,
  ocr_pages: 1,
  failed_pages: 1,
  quality_json: JSON.stringify({
    complete: false,
    import_ready: false,
    pages_missing_capture: [1],
    pages_truncated: [2],
    pages_missing_ocr_review: [0],
  }),
  error_message: '',
}

const pages = [
  {
    id: 101,
    job_id: 17,
    page_id: 'p1',
    page_name: 'Needs OCR review',
    page_path: 'Flow / Review',
    folder: 'Flow',
    order_index: 0,
    capture_status: 'success',
    ocr_status: 'unavailable',
    segment_count: 2,
    capture_truncated: false,
    dom_text: 'meaningful evidence',
    ocr_text: '',
    merged_text: 'meaningful evidence',
    quality_json: '{}',
    error_message: '',
    review_status: 'pending',
    review_comment: '',
    reviewed_at: null,
  },
  {
    id: 102,
    job_id: 17,
    page_id: 'p2',
    page_name: 'Capture failed',
    page_path: 'Flow / Failed',
    folder: 'Flow',
    order_index: 1,
    capture_status: 'failed',
    ocr_status: 'pending',
    segment_count: 0,
    capture_truncated: false,
    dom_text: '',
    ocr_text: '',
    merged_text: '',
    quality_json: '{}',
    error_message: 'capture failed',
    review_status: 'pending',
    review_comment: '',
    reviewed_at: null,
  },
]

function arrangeLoad() {
  mockGet.mockImplementation((url: string) => {
    if (url === '/lanhu-evidence/jobs/17') return Promise.resolve(job)
    if (url === '/lanhu-evidence/jobs/17/pages') {
      return Promise.resolve({ total: pages.length, page: 1, page_size: 20, items: pages })
    }
    if (url === '/lanhu-evidence/jobs/17/assets') {
      return Promise.resolve([
        {
          id: 501,
          job_id: 17,
          page_id: null,
          asset_type: 'word',
          relative_path: 'exports/evidence.docx',
          mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          width: 0,
          height: 0,
          scroll_top: 0,
          viewport_height: 0,
          sha256: 'abc',
        },
      ])
    }
    return Promise.reject(new Error(`unexpected GET ${url}`))
  })
}

describe('LanhuEvidenceJobDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ permissions: ['*'] })
    arrangeLoad()
  })

  it('shows the non-importable quality state and every blocking reason', async () => {
    render(<LanhuEvidenceJobDrawer open onOpenChange={() => {}} jobId={17} />)

    expect(await screen.findByText('不可导入')).toBeTruthy()
    expect(screen.getByText('缺少截图：第 2 页')).toBeTruthy()
    expect(screen.getByText('滚动截断：第 3 页')).toBeTruthy()
    expect(screen.getByText('缺少 OCR 或人工审核：第 1 页')).toBeTruthy()
    expect(screen.queryByText(/storage[\\/]/i)).toBeNull()
  })

  it('requires an auditable comment and only offers review for eligible pages', async () => {
    mockPost.mockResolvedValueOnce({ ...pages[0], review_status: 'approved' })
    render(<LanhuEvidenceJobDrawer open onOpenChange={() => {}} jobId={17} />)

    const reviewButtons = await screen.findAllByRole('button', { name: '人工审核' })
    expect(reviewButtons).toHaveLength(1)
    fireEvent.click(reviewButtons[0])

    const submit = screen.getByRole('button', { name: '批准该页' })
    expect(submit.hasAttribute('disabled')).toBe(true)
    fireEvent.change(screen.getByLabelText('审核备注'), { target: { value: '已核对原始设计稿' } })
    expect(submit.hasAttribute('disabled')).toBe(false)
    fireEvent.click(submit)

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/lanhu-evidence/pages/101/review',
      { approved: true, comment: '已核对原始设计稿' },
    ))
  })

  it('downloads exports through the authorized asset endpoint', async () => {
    const blob = new Blob(['evidence'])
    mockGet.mockImplementation((url: string, config?: unknown) => {
      if (url === '/lanhu-evidence/assets/501') {
        expect(config).toEqual({ responseType: 'blob' })
        return Promise.resolve(blob)
      }
      if (url === '/lanhu-evidence/jobs/17') return Promise.resolve(job)
      if (url === '/lanhu-evidence/jobs/17/pages') {
        return Promise.resolve({ total: pages.length, page: 1, page_size: 20, items: pages })
      }
      if (url === '/lanhu-evidence/jobs/17/assets') {
        return Promise.resolve([{
          id: 501,
          job_id: 17,
          page_id: null,
          asset_type: 'word',
          relative_path: 'exports/evidence.docx',
          mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          width: 0,
          height: 0,
          scroll_top: 0,
          viewport_height: 0,
          sha256: 'abc',
        }])
      }
      return Promise.reject(new Error(`unexpected GET ${url}`))
    })
    const createObjectURL = vi.fn(() => 'blob:evidence')
    const revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL })

    render(<LanhuEvidenceJobDrawer open onOpenChange={() => {}} jobId={17} />)
    fireEvent.click(await screen.findByRole('button', { name: '下载 Word' }))

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(
      '/lanhu-evidence/assets/501',
      { responseType: 'blob' },
    ))
    expect(createObjectURL).toHaveBeenCalledWith(blob)
    click.mockRestore()
  })

  it('switches to the immutable retry job returned by the API', async () => {
    const retryJob = { ...job, id: 18, status: 'pending', attempt_no: 2, parent_job_id: 17 }
    mockPost.mockResolvedValueOnce(retryJob)
    mockGet.mockImplementation((url: string) => {
      if (url === '/lanhu-evidence/jobs/17') return Promise.resolve(job)
      if (url === '/lanhu-evidence/jobs/18') return Promise.resolve(retryJob)
      if (url.endsWith('/pages')) return Promise.resolve({ total: 0, page: 1, page_size: 20, items: [] })
      if (url.endsWith('/assets')) return Promise.resolve([])
      return Promise.reject(new Error(`unexpected GET ${url}`))
    })

    render(<LanhuEvidenceJobDrawer open onOpenChange={() => {}} jobId={17} />)
    fireEvent.click(await screen.findByRole('button', { name: '重试' }))

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/lanhu-evidence/jobs/17/retry',
      {},
    ))
    expect(await screen.findByText(/#18/)).toBeTruthy()
  })
})
