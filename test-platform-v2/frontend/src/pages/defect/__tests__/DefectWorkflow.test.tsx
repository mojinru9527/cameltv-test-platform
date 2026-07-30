import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DefectItem } from '@/types'
import { STATUS_TRANSITIONS } from '../constants'
import DefectDetailSheet from '../DefectDetailSheet'
import DefectFormDialog from '../DefectFormDialog'

const apiMocks = vi.hoisted(() => ({
  transitionDefect: vi.fn(),
  updateDefect: vi.fn(),
  createDefect: vi.fn(),
}))

vi.mock('@/hooks/useApi', () => ({
  default: () => ({ data: [], refetch: vi.fn() }),
}))

vi.mock('@/api/defect', () => ({
  fetchTransitions: vi.fn(),
  transitionDefect: apiMocks.transitionDefect,
  fetchComments: vi.fn(),
  addComment: vi.fn(),
  fetchAttachments: vi.fn(),
  uploadAttachment: vi.fn(),
  getAttachmentUrl: vi.fn(),
  deleteAttachment: vi.fn(),
  createDefect: apiMocks.createDefect,
  updateDefect: apiMocks.updateDefect,
}))

vi.mock('@/api/integration', () => ({
  pushDefect: vi.fn(),
  pullDefect: vi.fn(),
}))

vi.mock('@/api/testcase', () => ({
  fetchTestCases: vi.fn().mockResolvedValue({ items: [] }),
}))

vi.mock('@/api/system', () => ({
  fetchUsers: vi.fn().mockResolvedValue([]),
}))

const openDefect: DefectItem = {
  id: 7,
  defect_id: 'BUG-0007',
  title: '登录失败',
  description: '正确密码无法登录',
  severity: 'P1',
  status: 'open',
  case_id: null,
  execution_id: null,
  assignee_id: 3,
  assignee_name: '测试员',
  external_id: '',
  external_url: '',
  creator_id: 2,
  creator_name: '管理员',
  case_title: '',
  resolved_at: null,
  created_at: '2026-07-29T00:00:00Z',
  updated_at: '2026-07-29T00:00:00Z',
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('缺陷状态机', () => {
  it('与后端合法流转保持一致', () => {
    expect(STATUS_TRANSITIONS).toEqual({
      open: ['confirmed', 'rejected'],
      confirmed: ['fixing', 'rejected'],
      fixing: ['pending_review'],
      pending_review: ['closed', 'fixing'],
      closed: [],
      rejected: ['open'],
    })
  })

  it('open 首步只显示确认和拒绝按钮，并通过 transition API 流转', async () => {
    const confirmed = { ...openDefect, status: 'confirmed' }
    apiMocks.transitionDefect.mockResolvedValue(confirmed)
    const onTransitioned = vi.fn()

    render(
      <DefectDetailSheet
        detail={openDefect}
        open
        onClose={vi.fn()}
        onTransitioned={onTransitioned}
        onMutated={vi.fn()}
        canSync={false}
      />,
    )

    expect(screen.getByRole('button', { name: /已确认/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /已拒绝/ })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /已关闭/ })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /已确认/ }))
    fireEvent.click(await screen.findByRole('button', { name: '确认流转' }))

    await waitFor(() => {
      expect(apiMocks.transitionDefect).toHaveBeenCalledWith(7, {
        to_status: 'confirmed',
        comment: undefined,
      })
      expect(onTransitioned).toHaveBeenCalledWith(confirmed)
    })
  })
})

describe('缺陷编辑', () => {
  it('不提供状态字段，更新请求也不直接写 status', async () => {
    apiMocks.updateDefect.mockResolvedValue({ ...openDefect, title: '更新后的标题' })

    render(
      <DefectFormDialog
        open
        editing={openDefect}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    )

    expect(screen.queryByLabelText('状态')).toBeNull()
    fireEvent.change(screen.getByLabelText('缺陷标题'), {
      target: { value: '更新后的标题' },
    })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => {
      expect(apiMocks.updateDefect).toHaveBeenCalledTimes(1)
    })
    const updateBody = apiMocks.updateDefect.mock.calls[0][1]
    expect(updateBody).not.toHaveProperty('status')
  })
})
