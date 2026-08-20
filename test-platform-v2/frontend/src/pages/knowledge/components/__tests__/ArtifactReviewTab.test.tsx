import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

const fetchAiArtifacts = vi.fn()
const approveArtifact = vi.fn()
const rejectArtifact = vi.fn()
const importArtifact = vi.fn()
const batchApproveArtifacts = vi.fn()
const batchRejectArtifacts = vi.fn()
const batchImportArtifacts = vi.fn()
const toastSuccess = vi.fn()
const toastError = vi.fn()

vi.mock('@/api/knowledge', () => ({
  fetchAiArtifacts: (...args: unknown[]) => fetchAiArtifacts(...args),
  approveArtifact: (...args: unknown[]) => approveArtifact(...args),
  rejectArtifact: (...args: unknown[]) => rejectArtifact(...args),
  importArtifact: (...args: unknown[]) => importArtifact(...args),
  batchApproveArtifacts: (...args: unknown[]) => batchApproveArtifacts(...args),
  batchRejectArtifacts: (...args: unknown[]) => batchRejectArtifacts(...args),
  batchImportArtifacts: (...args: unknown[]) => batchImportArtifacts(...args),
}))

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

const { default: ArtifactReviewTab } = await import('../ArtifactReviewTab')

function artifact(overrides: Record<string, unknown>) {
  return {
    id: 1,
    project_id: 1,
    artifact_type: 'functional_case',
    title: '登录功能用例',
    content_json: '{}',
    source_refs: '["dsh_task:1"]',
    confidence: 0.9,
    review_status: 'approved',
    imported_ref_type: '',
    imported_ref_id: null,
    created_at: '2026-08-20T00:00:00Z',
    ...overrides,
  }
}

function mockList(items: ReturnType<typeof artifact>[]) {
  fetchAiArtifacts.mockResolvedValue({ items, total: items.length, page: 1, page_size: 20 })
}

describe('ArtifactReviewTab 产物导入（requirement/ui_case 解禁）', () => {
  beforeEach(() => vi.clearAllMocks())

  it('ui_case 已采纳产物导入按钮可用，导入后提示用例库', async () => {
    mockList([artifact({ id: 7, artifact_type: 'ui_case', title: '首页 UI 用例' })])
    importArtifact.mockResolvedValue({ artifact_id: 7, ref_type: 'test_case', ref_id: 101, case_id: 101 })

    render(<ArtifactReviewTab />)

    const btn = await screen.findByLabelText('导入制品 首页 UI 用例')
    expect((btn as HTMLButtonElement).disabled).toBe(false)
    fireEvent.click(btn)
    await waitFor(() => expect(importArtifact).toHaveBeenCalledWith(7))
    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith('已导入用例库'))
  })

  it('requirement 已采纳产物导入按钮可用，导入后提示需求库', async () => {
    mockList([artifact({ id: 8, artifact_type: 'requirement', title: '用户端 14.2 需求分析' })])
    importArtifact.mockResolvedValue({ artifact_id: 8, ref_type: 'requirement_document', ref_id: 55 })

    render(<ArtifactReviewTab />)

    const btn = await screen.findByLabelText('导入制品 用户端 14.2 需求分析')
    expect((btn as HTMLButtonElement).disabled).toBe(false)
    fireEvent.click(btn)
    await waitFor(() => expect(importArtifact).toHaveBeenCalledWith(8))
    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith('已导入需求库'))
  })

  it('待审核产物显示采纳/驳回按钮，不显示导入按钮（守卫不回归）', async () => {
    mockList([artifact({ id: 9, review_status: 'pending', title: '待审产物' })])

    render(<ArtifactReviewTab />)

    expect(await screen.findByLabelText('采纳制品 待审产物')).toBeTruthy()
    expect(screen.getByLabelText('驳回制品 待审产物')).toBeTruthy()
    expect(screen.queryByLabelText('导入制品 待审产物')).toBeNull()
    expect(importArtifact).not.toHaveBeenCalled()
  })
})
