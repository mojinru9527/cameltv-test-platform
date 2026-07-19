import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/api/testcase', () => ({
  createTestCase: vi.fn(),
  updateTestCase: vi.fn(),
  reviewCase: vi.fn(),
  fetchReviewHistory: vi.fn().mockResolvedValue([]),
}))

import CaseDrawer from '../CaseDrawer'

const domains = [
  {
    id: 1,
    domain: '用户端',
    count: 0,
    modules: [{ id: 11, module: '登录', count: 0 }],
  },
]

describe('新建用例弹窗', () => {
  it('默认草稿并移除编号、标签和关联引用字段', () => {
    render(
      <CaseDrawer
        open
        editing={null}
        domains={domains}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('状态').textContent).toContain('草稿')
    expect(screen.queryByLabelText('用例编号')).toBeNull()
    expect(screen.queryByLabelText(/标签/)).toBeNull()
    expect(screen.queryByLabelText('关联引用')).toBeNull()
    expect(screen.queryByText('关联引用')).toBeNull()
  })

  it('模块、测试步骤和预期结果均为必填项', async () => {
    render(
      <CaseDrawer
        open
        editing={null}
        domains={domains}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => {
      expect(screen.getByText('请选择模块')).toBeTruthy()
      expect(screen.getByText('请输入测试步骤')).toBeTruthy()
      expect(screen.getByText('请输入预期结果')).toBeTruthy()
    })
  })

  it('编辑用例时把 JSON 测试步骤回显为编号换行文本', async () => {
    render(
      <CaseDrawer
        open
        editing={{
          id: 9,
          title: '取消关注弹窗',
          case_type: 'manual',
          priority: 'P1',
          status: 'active',
          domain: '用户端',
          module: '登录',
          preconditions: '已关注',
          steps: JSON.stringify([
            { step: 1, desc: '点击 Following', expected: '' },
            { step: 2, desc: '弹窗点取消', expected: '' },
          ]),
          expected_result: '仍为已关注',
        }}
        domains={domains}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    )

    await waitFor(() => {
      expect((screen.getByLabelText('测试步骤') as HTMLTextAreaElement).value).toBe(
        '1、点击 Following\n2、弹窗点取消',
      )
    })
  })
})
