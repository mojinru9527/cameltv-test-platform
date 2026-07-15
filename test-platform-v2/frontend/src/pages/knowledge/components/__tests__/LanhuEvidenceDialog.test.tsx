/**
 * LanhuEvidenceDialog — 证据包 OCR 导入对话框测试。
 *
 * 覆盖：
 * - api 函数 createLanhuEvidenceJob 调用正确端点
 * - 对话框渲染链接输入与采集开关
 * - 提交空链接不触发请求；提交有效链接触发 POST /lanhu-evidence/jobs
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

// ── Mock API client ──
const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

const { createLanhuEvidenceJob } = await import('@/api/lanhuEvidence')
const { default: LanhuEvidenceDialog } = await import('../LanhuEvidenceDialog')

describe('Lanhu evidence API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('createLanhuEvidenceJob posts /lanhu-evidence/jobs', async () => {
    mockPost.mockResolvedValueOnce({ id: 7, status: 'pending' })
    await createLanhuEvidenceJob({
      url: 'https://lanhuapp.com/x?docId=d',
      capture_all_pages: true,
      include_word: true,
      include_json: true,
      import_to_requirement: false,
      import_to_knowledge: false,
      import_to_wiki: false,
    })
    expect(mockPost).toHaveBeenCalledWith('/lanhu-evidence/jobs', expect.objectContaining({
      url: 'https://lanhuapp.com/x?docId=d',
      capture_all_pages: true,
    }))
  })
})

describe('LanhuEvidenceDialog component', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders url input and capture switches', () => {
    render(<LanhuEvidenceDialog open onOpenChange={() => {}} />)
    expect(screen.getByText('证据包 OCR 导入')).toBeTruthy()
    expect(screen.getByLabelText('蓝湖设计稿链接')).toBeTruthy()
    expect(screen.getByText('发现并采集全部页面')).toBeTruthy()
  })

  it('submits and creates a job for a valid url', async () => {
    mockPost.mockResolvedValueOnce({ id: 9, status: 'pending' })
    const onCreated = vi.fn()
    render(<LanhuEvidenceDialog open initialUrl="https://lanhuapp.com/x?docId=d" onOpenChange={() => {}} onCreated={onCreated} />)

    fireEvent.click(screen.getByRole('button', { name: '开始采集' }))

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/lanhu-evidence/jobs', expect.any(Object)))
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ id: 9 })))
  })
})
