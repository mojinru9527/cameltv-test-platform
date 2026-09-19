import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import EvidenceBundlePanel from '../EvidenceBundlePanel'
import type { EvidenceVerification } from '@/api/executionJobs'

const mockState: {
  data: EvidenceVerification | undefined
  isLoading: boolean
  isError: boolean
  error: Error | null
} = { data: undefined, isLoading: false, isError: false, error: null }

vi.mock('@/hooks/useApi', () => ({
  useApi: () => ({
    data: mockState.data,
    isLoading: mockState.isLoading,
    isRefetching: false,
    isError: mockState.isError,
    error: mockState.error,
    refetch: vi.fn(),
    setData: vi.fn(),
    abort: vi.fn(),
  }),
}))

const VERIFIED: EvidenceVerification = {
  job_id: 7,
  attempt: 1,
  verdict: 'verified',
  files: [
    { name: 'c1.request.json', evidence_type: 'REQUEST', status: 'ok', expected_sha256: 'a', actual_sha256: 'a' },
    { name: 'c1.response.json', evidence_type: 'RESPONSE', status: 'ok', expected_sha256: 'b', actual_sha256: 'b' },
  ],
  tampered: [],
  missing: [],
  extra: [],
  unclassified: [],
  completeness: { required: ['REQUEST', 'RESPONSE'], present: ['REQUEST', 'RESPONSE'], missing: [], complete: true },
}

const TAMPERED: EvidenceVerification = {
  ...VERIFIED,
  verdict: 'tampered',
  files: [
    VERIFIED.files[0],
    { name: 'c1.response.json', evidence_type: 'RESPONSE', status: 'tampered', expected_sha256: 'b', actual_sha256: 'X' },
  ],
  tampered: ['c1.response.json'],
  completeness: { required: ['REQUEST', 'RESPONSE'], present: ['REQUEST'], missing: ['RESPONSE'], complete: false },
}

beforeEach(() => {
  mockState.data = undefined
  mockState.isLoading = false
  mockState.isError = false
  mockState.error = null
})

function renderPanel() {
  return render(
    <MemoryRouter>
      <EvidenceBundlePanel jobId={7} />
    </MemoryRouter>,
  )
}

describe('EvidenceBundlePanel（Batch 261 / B4-1：篡改显红）', () => {
  it('未改动时给出通过结论与必需证据齐备', () => {
    mockState.data = VERIFIED
    renderPanel()
    expect(screen.getByTestId('verdict-verified')).toBeTruthy()
    expect(screen.getByText('必需证据齐备')).toBeTruthy()
  })

  it('篡改时显红并说明该证据不再作为放行依据', () => {
    mockState.data = TAMPERED
    renderPanel()
    const banner = screen.getByTestId('verdict-tampered')
    expect(banner.className).toContain('text-destructive')
    expect(screen.getByText(/1 个文件与 manifest 的 sha256 不一致/)).toBeTruthy()
    // 被改动的文件行本身也必须是 destructive
    const row = screen.getByTestId('evidence-file-c1.response.json')
    expect(row.className).toContain('text-destructive')
  })

  it('缺失的必需证据类型被单独列出（回答"还缺什么"）', () => {
    mockState.data = TAMPERED
    renderPanel()
    expect(screen.getByText(/缺少必需证据：RESPONSE/)).toBeTruthy()
  })

  it('未识别证据类型被显式提示（不静默丢弃）', () => {
    mockState.data = { ...VERIFIED, unclassified: ['weird.bin'] }
    renderPanel()
    expect(screen.getByText(/未识别证据类型/)).toBeTruthy()
  })

  it('加载中不显示通过结论（避免误判）', () => {
    mockState.isLoading = true
    renderPanel()
    expect(screen.queryByTestId('verdict-verified')).toBeNull()
  })
})
