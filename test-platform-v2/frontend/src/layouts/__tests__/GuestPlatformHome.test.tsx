import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import GuestPlatformHome from '../GuestPlatformHome'

describe('访客平台首页', () => {
  it('公开展示模块目录，点击模块时请求登录而不渲染业务内容', () => {
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
                { code: 'mindmap', name: '用例脑图', path: '/mindmap', icon: '', sort: 2 },
              ],
            },
          ]}
          registrationEnabled
          onRequireLogin={requireLogin}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: '先浏览平台，再登录开始工作' })).toBeTruthy()
    expect(screen.getByText('用例服务')).toBeTruthy()
    expect(screen.getByText('用例脑图')).toBeTruthy()
    expect(screen.getByRole('link', { name: '免费注册' }).getAttribute('href')).toBe('/register')

    fireEvent.click(screen.getByRole('button', { name: /打开用例脑图/ }))
    expect(requireLogin).toHaveBeenCalledWith('/mindmap', '用例脑图')
  })
})
