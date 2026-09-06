import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  createVersionTask: vi.fn(),
  generatePlanAi: vi.fn(),
  getPlan: vi.fn(),
  reviewPlanItem: vi.fn(),
  transitionVersionTask: vi.fn(),
  fetchRequirements: vi.fn(),
}))

vi.mock('@/api/versionTask', () => ({
  createVersionTask: mocks.createVersionTask,
  generatePlanAi: mocks.generatePlanAi,
  getPlan: mocks.getPlan,
  reviewPlanItem: mocks.reviewPlanItem,
  transitionVersionTask: mocks.transitionVersionTask,
}))
vi.mock('@/api/requirement', () => ({ fetchRequirements: mocks.fetchRequirements }))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

import VersionTasksPage from '../index'

const task = { id: 9, title: '体育验收', version: '16.0.0', status: 'draft' }
const draftItem = {
  id: 3,
  item_type: 'functional',
  title: '赛程主链',
  description: '验证赛程',
  confidence: 90,
  status: 'draft',
  question: '',
}

function renderPage() {
  return render(<MemoryRouter><VersionTasksPage /></MemoryRouter>)
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.fetchRequirements.mockResolvedValue({ items: [] })
  mocks.createVersionTask.mockResolvedValue(task)
  mocks.generatePlanAi.mockResolvedValue([draftItem])
  mocks.getPlan.mockResolvedValue([{ ...draftItem, status: 'adopted' }])
  mocks.reviewPlanItem.mockResolvedValue({ ...draftItem, status: 'adopted' })
  mocks.transitionVersionTask.mockResolvedValue({ ...task, status: 'plan_review' })
})

describe('版本任务三步向导', () => {
  it('创建任务后进入审方案，不跳转到执行页', async () => {
    renderPage()
    fireEvent.change(screen.getByLabelText('任务标题'), { target: { value: '体育验收' } })
    fireEvent.change(screen.getByLabelText('版本号'), { target: { value: '16.0.0' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))

    expect(await screen.findByRole('button', { name: '生成验收方案' })).toBeTruthy()
    expect(screen.queryByText('进入执行与证据')).toBeNull()
  })

  it('至少采纳或修订一条方案后才允许确认', async () => {
    renderPage()
    fireEvent.change(screen.getByLabelText('任务标题'), { target: { value: '体育验收' } })
    fireEvent.change(screen.getByLabelText('版本号'), { target: { value: '16.0.0' } })
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }))
    fireEvent.click(await screen.findByRole('button', { name: '生成验收方案' }))

    const confirm = await screen.findByRole('button', { name: '确认并进入待审' })
    expect((confirm as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: '采纳' }))
    await waitFor(() => expect((confirm as HTMLButtonElement).disabled).toBe(false))
  })
})
