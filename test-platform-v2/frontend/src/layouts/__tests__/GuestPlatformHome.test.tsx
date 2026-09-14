import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import GuestPlatformHome from '../GuestPlatformHome'

describe('访客平台首页', () => {
  it('优先展示任务入口，并在登录后进入目标路径', () => {
    const navigate = vi.fn()
    const requireLogin = vi.fn()
    render(
      <MemoryRouter>
        <GuestPlatformHome
          modules={[]}
          registrationEnabled
          onNavigate={navigate}
          onRequireLogin={requireLogin}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: '从测试任务开始，而不是先找模块' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '登录后开始需求测试' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '登录后做接口回归' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '登录后创建 UI 自动化' })).toBeTruthy()
    expect(screen.getByRole('button', { name: '登录后查看测试报告' })).toBeTruthy()
    expect(screen.getByRole('link', { name: '免费注册' }).getAttribute('href')).toBe('/register')

    fireEvent.click(screen.getByRole('button', { name: '登录后做接口回归' }))
    expect(requireLogin).toHaveBeenCalledWith('/apitest', '做接口回归')
    expect(navigate).not.toHaveBeenCalled()
  })

  it('按需展开模块目录并保留访客预览导航', () => {
    const navigate = vi.fn()
    render(
      <MemoryRouter>
        <GuestPlatformHome
          modules={[
            {
              code: 'quality',
              name: '质量管理',
              path: '/quality',
              icon: '',
              sort: 1,
              children: [
                { code: 'testcase', name: '用例服务', path: '/testcase', icon: '', sort: 1 },
                { code: 'mindmap', name: '思维导图', path: '/mindmap', icon: '', sort: 2 },
              ],
            },
          ]}
          registrationEnabled
          onNavigate={navigate}
          onRequireLogin={vi.fn()}
        />
      </MemoryRouter>,
    )

    const disclosure = screen.getByRole('button', { name: /展开模块/ })
    expect(disclosure.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByText('用例服务')).toBeNull()

    fireEvent.click(disclosure)
    expect(disclosure.getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByText('用例服务')).toBeTruthy()
    expect(screen.getByText('思维导图')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /查看思维导图功能/ }))
    expect(navigate).toHaveBeenCalledWith('/mindmap')
  })

  it('模块目录为空时给出明确兜底', () => {
    render(
      <MemoryRouter>
        <GuestPlatformHome
          modules={[]}
          registrationEnabled={false}
          onNavigate={vi.fn()}
          onRequireLogin={vi.fn()}
        />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: /展开模块/ }))
    expect(screen.getByText('暂无可浏览模块，请稍后重试或直接登录。')).toBeTruthy()
    expect(screen.queryByRole('link', { name: '免费注册' })).toBeNull()
  })
})
