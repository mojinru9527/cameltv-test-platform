import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DefectFormDialog from '../DefectFormDialog'

const apiMocks = vi.hoisted(() => ({
  createDefect: vi.fn(),
  updateDefect: vi.fn(),
}))

vi.mock('@/api/defect', () => ({
  createDefect: apiMocks.createDefect,
  updateDefect: apiMocks.updateDefect,
}))

vi.mock('@/api/testcase', () => ({
  fetchTestCases: vi.fn().mockResolvedValue({ items: [] }),
}))

vi.mock('@/api/system', () => ({
  fetchUsers: vi.fn().mockResolvedValue([]),
}))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('DefectFormDialog 失败态（Batch 148 P0-01）', () => {
  it('不选处理人提交：assignee_id 为 null 且成功时关闭弹窗', async () => {
    apiMocks.createDefect.mockResolvedValue({ id: 1 })
    const onSaved = vi.fn()
    const onClose = vi.fn()

    render(<DefectFormDialog open editing={null} onClose={onClose} onSaved={onSaved} />)

    fireEvent.change(screen.getByLabelText('缺陷标题'), { target: { value: '测试缺陷' } })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => {
      expect(apiMocks.createDefect).toHaveBeenCalledTimes(1)
    })
    const body = apiMocks.createDefect.mock.calls[0][0]
    expect(body.assignee_id).toBeNull()
    expect(onSaved).toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })

  it('保存失败：弹窗内显示可读错误、不关闭、不崩溃', async () => {
    apiMocks.createDefect.mockRejectedValue(
      new Error('请求参数校验失败：assignee_id: Input should be a valid integer'),
    )
    const onSaved = vi.fn()
    const onClose = vi.fn()

    render(<DefectFormDialog open editing={null} onClose={onClose} onSaved={onSaved} />)

    fireEvent.change(screen.getByLabelText('缺陷标题'), { target: { value: '测试缺陷' } })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('请求参数校验失败')
    expect(onSaved).not.toHaveBeenCalled()
    expect(onClose).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: '保存' })).toBeTruthy()
  })
})
