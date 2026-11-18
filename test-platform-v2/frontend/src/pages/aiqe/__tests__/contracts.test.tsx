import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  listContracts: vi.fn(),
  getContract: vi.fn(),
  createContract: vi.fn(),
  transitionContract: vi.fn(),
  approveAc: vi.fn(),
  getContractCoverage: vi.fn(),
  listCases: vi.fn(),
  reviewCase: vi.fn(),
}))

vi.mock('@/api/aiqeContracts', () => api)

const { default: ContractsPage } = await import('@/pages/aiqe/contracts')

const SUMMARY = {
  id: 'c-1',
  requirement_id: 'REQ-1001',
  revision: 1,
  title: '赛事发布后可见直播',
  status: 'DRAFT',
  revision_checksum: 'sha256:abcdef0123456789',
  created_at: new Date().toISOString(),
}

const DETAIL = {
  ...SUMMARY,
  project_id: 1,
  business_goal: '发布即播',
  actors: ['运营'],
  source_refs: ['prd:spec.md#直播'],
  ambiguities: [],
  approved_by: null,
  frozen_at: null,
  acceptance_criteria: [
    {
      ac_id: 'AC-001',
      priority: 'P0',
      oracle_type: 'product_rule',
      oracle_ref: 'PRD#1',
      platforms: ['web_desktop'],
      approval_status: 'PENDING',
    },
  ],
}

const CASE = {
  case_id: 'TC-900',
  title: '直播入口可见',
  priority: 'P0',
  automation_grade: 'A',
  review_status: 'DRAFT',
  contract_id: 'c-1',
  contract_revision: 1,
  covers_ac_ids: ['AC-001'],
  platform_targets: ['web_desktop'],
  oracle_ref: 'AC-001',
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ContractsPage />
    </MemoryRouter>,
  )
}

describe('ContractsPage', () => {
  beforeEach(() => {
    Object.values(api).forEach((fn) => fn.mockReset())
    api.listContracts.mockResolvedValue([SUMMARY])
    api.getContract.mockResolvedValue(DETAIL)
    api.getContractCoverage.mockResolvedValue({
      contract_id: 'c-1',
      coverage: { 'AC-001': 'PARTIAL' },
      uncovered: [],
      partial: ['AC-001'],
    })
    api.listCases.mockResolvedValue([CASE])
    api.transitionContract.mockResolvedValue({ ...DETAIL, status: 'REVIEW_REQUIRED' })
    api.approveAc.mockResolvedValue({ ac_id: 'AC-001', approval_status: 'APPROVED' })
    api.reviewCase.mockResolvedValue({ ...CASE, review_status: 'APPROVED' })
  })

  it('lists contracts and loads AC/coverage/cases on select', async () => {
    renderPage()
    expect(await screen.findByText('赛事发布后可见直播')).toBeTruthy()
    fireEvent.click(screen.getByText('赛事发布后可见直播'))

    await waitFor(() => expect(api.getContract).toHaveBeenCalledWith('c-1'))
    expect(api.getContractCoverage).toHaveBeenCalledWith('c-1')
    expect(api.listCases).toHaveBeenCalledWith({ contract_id: 'c-1' })

    expect(await screen.findByText('AC-001')).toBeTruthy()
    expect(screen.getByText('PARTIAL')).toBeTruthy()
    expect(screen.getByText('直播入口可见')).toBeTruthy()
    expect(screen.getByText('Grade')).toBeTruthy()
    expect(screen.getByText('A')).toBeTruthy()
  })

  it('submits a review transition', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('赛事发布后可见直播'))
    const button = await screen.findByText('提交评审')
    fireEvent.click(button)
    await waitFor(() => expect(api.transitionContract).toHaveBeenCalledWith('c-1', 'REVIEW_REQUIRED'))
  })

  it('approves an acceptance criterion', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('赛事发布后可见直播'))
    fireEvent.click(await screen.findByText('批准 AC'))
    await waitFor(() => expect(api.approveAc).toHaveBeenCalledWith('c-1', 'AC-001'))
  })

  it('reviews a case', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('赛事发布后可见直播'))
    fireEvent.click(await screen.findByText('通过'))
    await waitFor(() => expect(api.reviewCase).toHaveBeenCalledWith('TC-900', 'APPROVED'))
  })

  it('creates a contract draft from the form', async () => {
    api.createContract.mockResolvedValue(DETAIL)
    renderPage()
    fireEvent.change(screen.getByPlaceholderText('requirement_id（如 REQ-1001）'), {
      target: { value: 'REQ-1002' },
    })
    fireEvent.change(screen.getByPlaceholderText('标题'), { target: { value: '新需求' } })
    fireEvent.change(screen.getByPlaceholderText('来源引用（prd:spec.md#章节）'), {
      target: { value: 'prd:spec.md#1' },
    })
    fireEvent.change(screen.getByPlaceholderText('Given'), { target: { value: 'g' } })
    fireEvent.change(screen.getByPlaceholderText('When'), { target: { value: 'w' } })
    fireEvent.change(screen.getByPlaceholderText('Then（每行一条）'), { target: { value: 't1' } })
    fireEvent.change(screen.getByPlaceholderText('Oracle 引用（PRD#1；P0 必填）'), {
      target: { value: 'PRD#2' },
    })
    fireEvent.click(screen.getByText('创建 Draft'))
    await waitFor(() =>
      expect(api.createContract).toHaveBeenCalledWith(
        expect.objectContaining({
          requirement_id: 'REQ-1002',
          title: '新需求',
          source_refs: ['prd:spec.md#1'],
          acceptance_criteria: [
            expect.objectContaining({ ac_id: 'AC-001', priority: 'P0', oracle_ref: 'PRD#2' }),
          ],
        }),
      ),
    )
  })
})
