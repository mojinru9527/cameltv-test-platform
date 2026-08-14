import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import GuestPlatformHome from '../GuestPlatformHome'

describe('访客平台首页', () => {
  it('公开展示模块目录，浏览模块与开始使用采用不同动作', () => {
    const navigate = vi.fn()
    const requireLogin = vi.fn()
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
          onRequireLogin={requireLogin}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: '先浏览平台，再登录开始工作' })).toBeTruthy()
    expect(screen.getByText('用例服务')).toBeTruthy()
    expect(screen.getByText('思维导图')).toBeTruthy()
    expect(screen.getByRole('link', { name: '免费注册' }).getAttribute('href')).toBe('/register')

    fireEvent.click(screen.getByRole('button', { name: /查看思维导图功能/ }))
    expect(navigate).toHaveBeenCalledWith('/mindmap')
    expect(requireLogin).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /登录并开始使用/ }))
    expect(requireLogin).toHaveBeenCalledWith('/workbench', '工作台')
  })
})
