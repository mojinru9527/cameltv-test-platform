import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import GuestModulePreview from '../GuestModulePreview'
import { resolveGuestModule } from '../guestModuleCatalog'

describe('访客模块说明页', () => {
  it('挂载时只展示能力，显式开始使用后才请求登录', () => {
    const requireLogin = vi.fn()
    render(
      <MemoryRouter>
        <GuestModulePreview
          module={resolveGuestModule('/testcase')}
          path="/testcase"
          registrationEnabled
          onRequireLogin={requireLogin}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: '用例服务' })).toBeTruthy()
    expect(screen.getAllByRole('heading', { level: 3 }).length).toBeGreaterThanOrEqual(3)
    expect(requireLogin).not.toHaveBeenCalled()
    expect(screen.getByRole('link', { name: '免费注册' }).getAttribute('href')).toBe('/register')

    fireEvent.click(screen.getByRole('button', { name: '登录后使用用例服务' }))
    expect(requireLogin).toHaveBeenCalledWith('/testcase', '用例服务')
  })

  it('注册关闭时不展示注册入口', () => {
    render(
      <MemoryRouter>
        <GuestModulePreview
          module={resolveGuestModule('/mindmap')}
          path="/mindmap"
          registrationEnabled={false}
          onRequireLogin={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.queryByRole('link', { name: '免费注册' })).toBeNull()
  })
})
